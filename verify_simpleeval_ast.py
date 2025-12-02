from simpleeval import SimpleEval
import ast

def test_ast():
    s = SimpleEval()
    expr = "1 + 1"

    try:
        node = s.parse(expr)
        print(f"Node type: {type(node)}")

        if hasattr(s, '_eval'):
            val_node = node
            if hasattr(node, 'value'):
                 val_node = node.value
                 print("Unwrapped node.value")

            s.names = {}
            result = s._eval(val_node)
            print(f"_eval result: {result}")
        else:
            print("No _eval method.")

    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_ast()
