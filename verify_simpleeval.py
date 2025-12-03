from simpleeval import SimpleEval

def test_dot_notation():
    s = SimpleEval()

    # Test 1: Dict access
    my_dict = {"social": 10}
    context_dict = {"skills": my_dict}
    s.names = context_dict

    print(f"Type of skills: {type(my_dict)}")

    try:
        # verifying standard python behavior
        val = my_dict.social
    except AttributeError:
        print("Standard Python: Dict does not support dot access.")

    try:
        result = s.eval("skills.social > 5")
        print(f"SimpleEval: Dict dot notation: {result}")
    except Exception as e:
        print(f"SimpleEval: Dict dot notation failed: {e}")

if __name__ == "__main__":
    test_dot_notation()
