import sys
import inspect
import traceback
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from api import app
import tests.test_auth as t_auth
import tests.test_recruitment as t_rec
import tests.test_recommendations as t_recom
import tests.test_admin as t_adm


def run_all_tests():
    print("=" * 65)
    print("JOBBRIDGE AUTOMATED TEST SUITE (UNITTEST / BUILT-IN RUNNER)")
    print("=" * 65)

    test_modules = [
        ("Authentication & Roles", t_auth),
        ("Recruitment & Applications", t_rec),
        ("Recommendations & Readiness", t_recom),
        ("Administration & Security", t_adm)
    ]

    total_run = 0
    total_passed = 0
    total_failed = 0
    failures = []

    app.config["TESTING"] = True

    for suite_name, mod in test_modules:
        print(f"\n--- Suite: {suite_name} ---")
        functions = [f for name, f in inspect.getmembers(mod, inspect.isfunction) if name.startswith("test_")]

        for fn in functions:
            total_run += 1
            test_name = fn.__name__
            try:
                # Check if fn expects client parameter
                sig = inspect.signature(fn)
                if "client" in sig.parameters:
                    with app.test_client() as client:
                        fn(client)
                else:
                    fn()

                print(f"  [PASS] {test_name}")
                total_passed += 1
            except Exception as e:
                print(f"  [FAIL] {test_name}: ({e})")
                total_failed += 1
                failures.append((suite_name, test_name, traceback.format_exc()))

    print("\n" + "=" * 65)
    print(f"TEST RUN SUMMARY: {total_run} tests run")
    print(f"PASSED: {total_passed} | FAILED: {total_failed}")
    print("=" * 65)

    if failures:
        print("\nFAILURE DETAILS:")
        for suite, name, tb in failures:
            print(f"\n[{suite}] {name}:")
            print(tb)
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED SUCCESSFULLY! 100% PASS RATE.\n")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
