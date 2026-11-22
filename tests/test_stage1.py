import tempfile
from pathlib import Path
import pytest
import numpy as np

from stage1_detect import detect
from stage1_detect.inputs import parse_verilog_ports, generate_tvla_inputs, save_test_inputs, load_test_inputs
from stage1_detect.leakage_model import hamming_weight_int, hamming_distance_int, compute_signal_leakage
from stage1_detect.tvla import compute_welch_t_test, evaluate_tvla


def test_hamming_calculations():
    assert hamming_weight_int(0) == 0
    assert hamming_weight_int(1) == 1
    assert hamming_weight_int(7) == 3   # 0b111 -> 3
    assert hamming_weight_int(15) == 4  # 0b1111 -> 4

    assert hamming_distance_int(0, 0) == 0
    assert hamming_distance_int(0, 1) == 1
    assert hamming_distance_int(1, 2) == 2  # 0b01 -> 0b10 : 2 transitions
    assert hamming_distance_int(7, 0) == 3


def test_parse_ports():
    code = Path("designs/flawed_and.v").read_text(encoding="utf-8")
    ports = parse_verilog_ports(code, "flawed_and")
    assert ports["top_module"] == "flawed_and"
    assert ports["clock"] == "clk"
    input_names = [inp["name"] for inp in ports["inputs"]]
    assert "clk" in input_names
    assert "a0" in input_names and "a1" in input_names
    assert "b0" in input_names and "b1" in input_names
    assert "r" in input_names


def test_test_inputs_roundtrip(tmp_path):
    code = Path("designs/flawed_and.v").read_text(encoding="utf-8")
    ports = parse_verilog_ports(code, "flawed_and")
    tvla_data = generate_tvla_inputs(ports, num_traces=20, cycles_per_trace=3)
    assert tvla_data["num_traces"] == 20
    assert len(tvla_data["traces"]) == 20

    out_file = tmp_path / "inputs.json"
    save_test_inputs(tvla_data, out_file)
    loaded = load_test_inputs(out_file)
    assert loaded["num_traces"] == 20
    assert len(loaded["traces"]) == 20


def test_tvla_synthetic_separation():
    # Group 0: mean 0, Group 1: mean 5. Clear leakage.
    rng = np.random.default_rng(42)
    g0 = rng.normal(loc=0.0, scale=1.0, size=(100, 2))
    g1 = rng.normal(loc=5.0, scale=1.0, size=(100, 2))
    t_stat = compute_welch_t_test(g0, g1)
    assert np.all(np.abs(t_stat) > 10.0)

    # Group 0 and Group 1 with same mean: no leakage (|t| < 4.5)
    g0_same = rng.normal(loc=1.0, scale=1.0, size=(100, 2))
    g1_same = rng.normal(loc=1.0, scale=1.0, size=(100, 2))
    t_stat_same = compute_welch_t_test(g0_same, g1_same)
    assert np.all(np.abs(t_stat_same) < 4.5)


def test_detect_flawed_and():
    # Run detector on flawed_and.v
    report = detect.run("designs/flawed_and.v", "flawed_and", num_traces=600, noise_std=0.2)

    # Verify standard interface format
    assert report["design"] == "designs/flawed_and.v"
    assert report["top_module"] == "flawed_and"
    assert report["leakage_model"] == "hamming_weight"
    assert report["num_traces"] == 600
    assert report["leaky"] is True
    assert len(report["findings"]) > 0

    found_signals = [f["signal"] for f in report["findings"]]
    # Should catch either unmasked wire 'a', 'b', or 'y'
    assert any(sig in found_signals for sig in ["a", "b", "y"])

    for f in report["findings"]:
        assert "signal" in f
        assert "cycles" in f and len(f["cycles"]) > 0
        assert f["t_statistic"] > 4.5
        assert f["threshold"] == 4.5


def test_detect_secure_design(tmp_path):
    # Domain-Oriented Masking (DOM) / properly masked AND gate
    secure_verilog = """
module secure_and(
    input  clk,
    input  a0, a1,
    input  b0, b1,
    input  r,
    output y0, y1
);
    reg t00, t01, t10, t11;
    always @(posedge clk) begin
        t00 <= a0 & b0;
        t01 <= (a0 & b1) ^ r;
        t10 <= (a1 & b0) ^ r;
        t11 <= a1 & b1;
    end
    assign y0 = t00 ^ t01;
    assign y1 = t11 ^ t10;
endmodule
"""
    vfile = tmp_path / "secure_and.v"
    vfile.write_text(secure_verilog, encoding="utf-8")

    report = detect.run(str(vfile), "secure_and", num_traces=600, noise_std=0.5)

    assert report["design"] == str(vfile)
    assert report["top_module"] == "secure_and"
    assert report["leaky"] is False
    assert report["findings"] == []
