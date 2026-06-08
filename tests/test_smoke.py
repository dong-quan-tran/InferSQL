from bastionquant.settings import load_config


def test_load_config_smoke():
    config = load_config("configs/base.yaml")
    assert "data" in config
    assert "symbols" in config["data"]
    assert len(config["data"]["symbols"]) > 0