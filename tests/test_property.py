#test/test_property.py
from hypothesis import given, settings, strategies as st
import pytest
from app.utils import transform_data


task_strategy = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=1, max_value=100),
        "raw_value": st.integers(min_value=1, max_value=100),
    }
)


@given(task_strategy)
@settings(max_examples=50)
def test_transform_is_idempotent(data):
    transformed = transform_data(data)
    assert transform_data(transformed) == transformed


@given(st.integers(min_value=1, max_value=100))
@settings(max_examples=50)
def test_transform_output_positive(raw_value):
    data = {"id": 1, "raw_value": raw_value}
    result = transform_data(data)
    assert result["value"] == raw_value * 2
    assert result["value"] > 0


@given(task_strategy)
@settings(max_examples=50)
def test_transform_never_raises_on_valid_input(data):
    try:
        transform_data(data)
    except Exception as e:
        pytest.fail(f"transform_data() raised {type(e).__name__} unexpectedly!")