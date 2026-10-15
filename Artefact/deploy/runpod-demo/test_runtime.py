import hashlib
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))
from runtime import assets, launch


class RuntimeTests(unittest.TestCase):
    def test_defaults_and_asset_revisions(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"QA_DATA_DIR": directory}, clear=True):
            volume = launch.configure()
            manifest = assets.read_manifest()
            self.assertEqual(os.environ["OLLAMA_HOST"], "127.0.0.1:11434")
            self.assertEqual(os.environ["ENABLE_EVALUATION_API"], "false")
            self.assertEqual(os.environ["QUEUE_CONCURRENCY"], "1")
            self.assertEqual(os.environ["KB_REVISION"], manifest["knowledge_base"]["revision"])
            self.assertEqual(os.environ["EMBEDDING_REVISION"], manifest["embedding"]["revision"])
            self.assertTrue(Path(os.environ["KB_CACHE_DIR"]).is_relative_to(volume))
            self.assertTrue((volume / "ollama").is_dir())

    def test_three_active_four_waiting_settings(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "QA_DATA_DIR": directory, "QUEUE_CONCURRENCY": "3", "MAX_QUEUE": "4"
        }, clear=True):
            launch.configure()
            self.assertEqual(os.environ["QUEUE_CONCURRENCY"], "3")
            self.assertEqual(os.environ["OLLAMA_NUM_PARALLEL"], "3")
            self.assertEqual(os.environ["MAX_QUEUE"], "4")
            self.assertEqual(os.environ["QUEUE_WAIT_TIMEOUT"], "120")
            self.assertEqual(os.environ["OLLAMA_MAX_LOADED_MODELS"], "1")

    def test_invalid_parallel_configuration_is_rejected(self):
        for settings in ({"QUEUE_CONCURRENCY": "5"}, {"QUEUE_CONCURRENCY": "3", "OLLAMA_NUM_PARALLEL": "4"}):
            with patch.dict(os.environ, settings, clear=True):
                with self.assertRaises(ValueError):
                    launch.configure()

    def test_requires_persistent_storage(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"QA_DATA_DIR": directory + "/missing"}, clear=True):
            with self.assertRaises(RuntimeError):
                launch.configure()

    def test_missing_default_or_duplicate_models_rejected(self):
        for values in ["two", "one,one", "one,unknown", ""]:
            with patch.dict(os.environ, {"DEFAULT_MODEL_KEY": "one", "DEMO_MODELS": values}, clear=True):
                with self.assertRaises(ValueError):
                    launch.selected_models({"one": {}, "two": {}})

    def test_model_order_preserved(self):
        with patch.dict(os.environ, {"DEFAULT_MODEL_KEY": "one", "DEMO_MODELS": "two,one"}, clear=True):
            self.assertEqual(launch.selected_models({"one": {}, "two": {}}), ["two", "one"])

    def test_knowledge_base_uses_pinned_dataset(self):
        with patch.dict(os.environ, {"KB_CACHE_DIR": "/volume/kb", "HF_TOKEN": "test"}, clear=True), patch.object(launch, "ensure_asset") as download:
            launch.prepare_knowledge_base()
            manifest = assets.read_manifest()["knowledge_base"]
            self.assertEqual(download.call_count, 2)
            for call, record in zip(download.call_args_list, manifest["files"]):
                self.assertEqual(call.args, ("/volume/kb", manifest["repo_id"], manifest["revision"], record))
                self.assertEqual(call.kwargs, {"repo_type": "dataset", "token": "test"})

    def test_registered_model_is_reused_but_changed_prompt_registers_again(self):
        asset = assets.read_manifest()["models"]["llama3.2-base"]
        cfg = {"ollama_name": "llama3.2-base", "gguf_repo": asset["repo_id"],
               "gguf_filename": asset["filename"], "system_role": True, "repeat_penalty": 1.0}
        config = types.ModuleType("app.config")
        config.MODEL_REGISTRY = {"llama3.2-base": cfg}
        setup = types.ModuleType("deploy.setup_ollama")
        setup.build_modelfile_content = Mock(return_value="original prompt")
        process = Mock()
        process.poll.return_value = None
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"QA_DATA_DIR": directory, "DEFAULT_MODEL_KEY": "llama3.2-base"}, clear=True):
            volume = launch.configure()
            with patch.dict(sys.modules, {"app.config": config, "deploy.setup_ollama": setup}), \
                 patch.object(launch, "get_json", return_value={"models": [{"name": "llama3.2-base:latest"}]}), \
                 patch.object(launch, "ensure_asset", return_value=volume / "model.gguf"), \
                 patch.object(launch.subprocess, "run") as register:
                launch.register_models(volume, process)
                self.assertEqual(register.call_count, 1)
                launch.register_models(volume, process)
                self.assertEqual(register.call_count, 1)
                setup.build_modelfile_content.return_value = "updated prompt"
                launch.register_models(volume, process)
                self.assertEqual(register.call_count, 2)
                process.poll.return_value = 1
                with self.assertRaisesRegex(RuntimeError, "Ollama stopped"):
                    launch.register_models(volume, process)


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.record = {"filename": "model.bin", "bytes": 4, "sha256": hashlib.sha256(b"test").hexdigest()}

    def test_existing_asset_is_verified_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / self.record["filename"]
            path.write_bytes(b"test")
            self.assertEqual(assets.ensure_asset(directory, "repo", "revision", self.record), path)
            self.assertTrue(path.with_name(path.name + ".verified.json").exists())
            path.write_bytes(b"evil")
            # Force a distinct timestamp even on filesystems with coarse clock resolution.
            os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000_000))
            with self.assertRaisesRegex(ValueError, "checksum"):
                assets.ensure_asset(directory, "repo", "revision", self.record)

    def test_bad_size_and_path_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / self.record["filename"]
            path.write_bytes(b"shorter")
            with self.assertRaisesRegex(ValueError, "size"):
                assets.verify_file(path, self.record)
            for filename in ("../secret", "nested/file", ".."):
                with self.assertRaises(ValueError):
                    assets.asset_path(directory, {**self.record, "filename": filename})

    def test_download_pins_revision_and_checks_returned_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            def download(**kwargs):
                (Path(kwargs["local_dir"]) / kwargs["filename"]).write_bytes(b"test")
            hub = types.ModuleType("huggingface_hub")
            hub.hf_hub_download = Mock(side_effect=download)
            with patch.dict(sys.modules, {"huggingface_hub": hub}):
                assets.ensure_asset(directory, "owner/repo", "exact-commit", self.record, repo_type="dataset", token="test")
                self.assertEqual(hub.hf_hub_download.call_args.kwargs["revision"], "exact-commit")
                self.assertEqual(hub.hf_hub_download.call_args.kwargs["repo_type"], "dataset")
                assets.ensure_asset(directory, "owner/repo", "exact-commit", self.record)
                self.assertEqual(hub.hf_hub_download.call_count, 1)

    def test_registry_mismatch_fails_before_download(self):
        with self.assertRaisesRegex(ValueError, "registry"):
            assets.validate_registry({"new-model": {"gguf_repo": "other", "gguf_filename": "x"}}, assets.read_manifest())


if __name__ == "__main__":
    unittest.main()
