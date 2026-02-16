import pytest
from src.candidate_function import FunctionManager
from src.instance import Instance
from src.outputs.verilog_skolem import write_verilog_skolem


class TestVerilogSkolem:
    @pytest.fixture
    def manager(self):
        return FunctionManager()

    @pytest.fixture
    def simple_instance(self):
        # 2 Universal (x1, x2), 1 Existential (y3)
        # 2 Universal (x1, x2), 1 Existential (y3)
        from src.dependency_schemes.trivial import TrivialDependencyScheme

        quantifiers = [("a", [1, 2]), ("e", [3])]
        # No clauses needed for skolem generation test
        inst = Instance(3, 0, quantifiers, [], TrivialDependencyScheme)
        return inst

    def test_simple_output(self, manager, simple_instance, tmp_path):
        # y3 = x1 & x2
        x1 = manager.get_lit(1)
        x2 = manager.get_lit(2)
        func = manager.get_and([x1, x2])

        candidates = {3: func}
        output_path = tmp_path / "simple.v"

        write_verilog_skolem(output_path, simple_instance, candidates)

        content = output_path.read_text()
        assert "module SkolemFormula" in content
        assert "input 1, 2;" in content
        assert "output 3;" in content
        # Check for wire definition and assignment
        assert "wire w_" in content
        assert "assign w_" in content
        assert "assign 3 = w_" in content

    def test_dag_reuse(self, manager, tmp_path):
        # 4 Inputs, 2 Outputs
        # 4 Inputs, 2 Outputs
        from src.dependency_schemes.trivial import TrivialDependencyScheme

        quantifiers = [("a", [1, 2, 3, 4]), ("e", [5, 6])]
        inst = Instance(6, 0, quantifiers, [], TrivialDependencyScheme)

        # Shared node: M = x1 | x2 (OR node)
        # o5 = M & x3 (AND node)
        # o6 = M & x4 (AND node)
        # Alternating types prevents flattening.

        x1 = manager.get_lit(1)
        x2 = manager.get_lit(2)
        x3 = manager.get_lit(3)
        x4 = manager.get_lit(4)

        mid = manager.get_or([x1, x2])

        f5 = manager.get_and([mid, x3])
        f6 = manager.get_and([mid, x4])

        candidates = {5: f5, 6: f6}
        output_path = tmp_path / "reuse.v"
        write_verilog_skolem(output_path, inst, candidates)

        content = output_path.read_text()

        # Expect 3 wires:
        # w_mid = i1 | i2
        # w_5 = w_mid & i3
        # w_6 = w_mid & i4

        assert content.count("wire w_") == 3
        # Logic for mid should appear once (one OR operation)
        assert content.count("|") == 1

    def test_constants(self, manager, simple_instance, tmp_path):
        # y3 = True
        func = manager.get_true()
        candidates = {3: func}
        output_path = tmp_path / "const.v"
        write_verilog_skolem(output_path, simple_instance, candidates)

        content = output_path.read_text()
        assert "assign 3 = 1'b1;" in content

    def test_io_ports(self, manager, tmp_path):
        from src.dependency_schemes.trivial import TrivialDependencyScheme

        quantifiers = [("a", [1, 2]), ("e", [3, 4])]
        inst = Instance(4, 0, quantifiers, [], TrivialDependencyScheme)

        candidates = {3: manager.get_lit(1), 4: manager.get_lit(2)}

        output_path = tmp_path / "ports.v"
        write_verilog_skolem(output_path, inst, candidates)

        content = output_path.read_text()
        assert "input 1, 2;" in content
        assert "output 3, 4;" in content

    def test_mixed_polarity(self, manager, simple_instance, tmp_path):
        # y3 = ~x1
        func = manager.get_lit(-1)
        candidates = {3: func}

        output_path = tmp_path / "polarity.v"
        write_verilog_skolem(output_path, simple_instance, candidates)

        content = output_path.read_text()
        assert "assign 3 = ~1;" in content

    def test_disjoint_components(self, manager, tmp_path):
        from src.dependency_schemes.trivial import TrivialDependencyScheme

        quantifiers = [("a", [1, 2]), ("e", [3, 4])]
        inst = Instance(4, 0, quantifiers, [], TrivialDependencyScheme)

        c3 = manager.get_lit(1)
        c4 = manager.get_lit(2)
        candidates = {3: c3, 4: c4}

        output_path = tmp_path / "disjoint.v"
        write_verilog_skolem(output_path, inst, candidates)

        content = output_path.read_text()
        assert "assign 3 = 1;" in content
        assert "assign 4 = 2;" in content

    def test_large_function(self, manager, tmp_path):
        # Build a deep alternating tree to avoid flattening
        # (x1 & x2) | (x3 & x4) ...
        # Need enough variables
        num_inputs = 100
        num_inputs = 100
        quantifiers = [
            ("a", list(range(1, num_inputs + 1))),
            ("e", [num_inputs + 1]),
        ]
        from src.dependency_schemes.trivial import TrivialDependencyScheme

        inst = Instance(num_inputs + 1, 0, quantifiers, [], TrivialDependencyScheme)

        current_layer = [manager.get_lit(i) for i in range(1, num_inputs + 1)]

        # Build layers
        layer_num = 0
        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer) - 1, 2):
                left_node = current_layer[i]
                right_node = current_layer[i + 1]

                # Alternate AND/OR to prevent flattening
                if layer_num % 2 == 0:
                    node = manager.get_and([left_node, right_node])
                else:
                    node = manager.get_or([left_node, right_node])
                next_layer.append(node)

            current_layer = next_layer
            layer_num += 1

        root = current_layer[0]
        output_var = num_inputs + 1
        candidates = {output_var: root}

        output_path = tmp_path / "large.v"
        write_verilog_skolem(output_path, inst, candidates)

        content = output_path.read_text()

        # Verify significant size
        assert content.count("wire w_") >= 50

        # Check output assignment uses a wire
        assert f"assign {output_var} = w_" in content

        # Verify line lengths
        lines = content.splitlines()
        for line in lines:
            assert len(line) < 1000, f"Line too long: {len(line)}"
