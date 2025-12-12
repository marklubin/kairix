import unittest

import pytest


# Example 1: Skip entire test class
@pytest.mark.skip(reason="Not implemented yet")
class TestSkippedClass:
    def test_something(self):
        assert True


# Example 2: Skip conditionally
@pytest.mark.skipif(condition=True, reason="Skipping on this platform")
class TestConditionalSkip:
    def test_something(self):
        assert True


# Example 3: Mark as expected to fail
@pytest.mark.xfail(reason="Known bug")
class TestExpectedFailure:
    def test_something(self):
        raise AssertionError()  # This will be marked as XFAIL, not FAILED


# Example 4: Custom markers
@pytest.mark.integration
@pytest.mark.slow
class TestIntegration:
    """Tests marked with custom markers can be filtered."""

    def test_something(self):
        assert True


@pytest.skip
# Example 5: Skip individual tests in a class
class TestPartialSkip:
    def test_normal(self):
        assert True

    @pytest.mark.skip(reason="Not ready")
    def test_skipped(self):
        raise AssertionError()

    @pytest.mark.skipif(not hasattr(str, "removeprefix"), reason="Requires Python 3.9+")
    def test_conditional(self):
        assert "hello".removeprefix("he") == "llo"


@pytest.skip
# Example 6: Parametrized tests with marks
class TestParametrized:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (1, 1),
            pytest.param(2, 3, marks=pytest.mark.xfail(reason="Wrong expectation")),
            pytest.param(3, 3, marks=pytest.mark.skip(reason="Skip this case")),
        ],
    )
    def test_values(self, value, expected):
        assert value == expected

    # Skip entire class
    @unittest.skip("Demonstrating class skip")
    class TestSkippedClass(unittest.TestCase):
        def test_something(self):
            self.assertTrue(True)

    # Skip unless condition is met
    # @unittest.skipUnless(sys.version_info >= (3, 10), "Requires Python 3.10+")
    class TestVersionSpecific(unittest.TestCase):
        def test_something(self):
            self.assertTrue(True)
