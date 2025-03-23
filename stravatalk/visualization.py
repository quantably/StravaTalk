"""Visualization module for Strava data."""

import pandas as pd
import altair as alt
import streamlit as st
from typing import List
import datetime

TIME_FORMAT_EXPR = "datum.value >= 60 ? (floor(datum.value/60) >= 60 ? floor(floor(datum.value/60)/60) + ':' + (floor(datum.value/60) % 60 < 10 ? '0' : '') + toString(floor(datum.value/60) % 60) + ':' + (floor(datum.value % 60) < 10 ? '0' : '') + toString(floor(datum.value % 60)) : floor(datum.value/60) + ':' + (floor(datum.value % 60) < 10 ? '0' : '') + toString(floor(datum.value % 60))) : datum.value + ':00'"


def validate_chart_inputs(data, x_column, y_columns):
    """Validate chart inputs and return valid columns.

    Returns:
        tuple: (is_valid, valid_y_columns, error_message)
    """
    if x_column not in data.columns:
        return (
            False,
            [],
            f"X-axis column '{x_column}' not in data columns: {list(data.columns)}",
        )

    valid_y_columns = [col for col in y_columns if col in data.columns]
    if not valid_y_columns:
        return (
            False,
            [],
            f"None of the Y-axis columns {y_columns} found in data columns: {list(data.columns)}",
        )

    return True, valid_y_columns, None


def format_time_value(minutes: float) -> str:
    """Format time values in HH:MM:SS format."""
    total_seconds = int(minutes * 60)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


def format_strava_units(
    df: pd.DataFrame, x_column: str, y_columns: List[str]
) -> pd.DataFrame:
    """Format data with appropriate units for Strava metrics."""
    df_formatted = df.copy()

    for col in df_formatted.columns:
        if (
            "date" in col.lower()
            or "time" in col.lower()
            and df_formatted[col].dtype == "object"
        ):
            try:
                df_formatted[col] = pd.to_datetime(df_formatted[col])
            except:
                pass

    pace_cols = [col for col in df_formatted.columns if "pace" in col.lower()]
    for col in pace_cols:
        if df_formatted[col].dtype in ["float64", "float32", "int64", "int32"]:
            df_formatted[col] = df_formatted[col].apply(format_time_value)

    return df_formatted


def is_temporal_column(df: pd.DataFrame, column: str) -> bool:
    """Check if a column contains date/time values."""
    if column not in df.columns:
        return False
    if pd.api.types.is_datetime64_any_dtype(df[column]):
        return True

    date_terms = ["date", "time", "day", "month", "year"]
    if any(term in column.lower() for term in date_terms) and not df.empty:
        sample = df[column].iloc[0]
        if isinstance(sample, (pd.Timestamp, datetime.datetime, datetime.date)):
            return True
        if isinstance(sample, str):
            try:
                pd.to_datetime(sample)
                return True
            except:
                pass
    return False


def get_formatted_axis(df: pd.DataFrame, column: str, is_y_axis=False) -> alt.X:
    """Create a formatted axis configuration based on column name and data type."""
    axis_class = alt.Y if is_y_axis else alt.X
    col_lower = column.lower()

    if is_temporal_column(df, column):
        return axis_class(
            column + ":T", title=column, axis=alt.Axis(format="%d/%m/%y", labelAngle=45)
        )

    if (
        "_minutes" in col_lower
        or "time_min" in col_lower
        or any(time_term in col_lower for time_term in ["time", "elapsed", "moving"])
    ):
        title = column if "_minutes" in col_lower else f"{column} (minutes)"
        return axis_class(
            column, title=title, axis=alt.Axis(labelExpr=TIME_FORMAT_EXPR)
        )

    if "distance_km" in col_lower or column.endswith("_km"):
        return axis_class(column, title=column)
    elif "distance" in col_lower:
        return axis_class(column, title=f"{column} (km)")

    elif "pace" in col_lower and "_min_mi" in col_lower:
        return axis_class(column, title=column)

    return axis_class(column)


def create_visualization(
    df: pd.DataFrame, x_column: str, y_columns: List[str], chart_type: str = "line"
) -> alt.Chart:
    """Create a visualization based on the data and column specifications."""
    if x_column not in df.columns:
        raise ValueError(f"X-axis column '{x_column}' not found in data")

    missing_y_cols = [col for col in y_columns if col not in df.columns]
    if missing_y_cols:
        raise ValueError(
            f"Y-axis column(s) not found in data: {', '.join(missing_y_cols)}"
        )

    df = format_strava_units(df.copy(), x_column, y_columns)

    chart_creators = {
        "line": lambda: create_line_chart(df, x_column, y_columns, False),
        "area": lambda: create_line_chart(df, x_column, y_columns, True),
        "bar": lambda: create_bar_chart(df, x_column, y_columns[0]),
        "scatter": lambda: create_scatter_chart(df, x_column, y_columns[0]),
        "pie": lambda: create_pie_chart(df, x_column, y_columns[0]),
    }

    chart = chart_creators.get(chart_type, chart_creators["line"])()

    title = f"{', '.join(y_columns)} by {x_column}"
    return chart.properties(title=title).interactive()


def create_line_chart(
    df: pd.DataFrame, x_column: str, y_columns: List[str], area: bool = False
) -> alt.Chart:
    """Create a line chart (or area chart if area=True)."""
    mark_type = "area" if area else "line"
    mark_params = {"opacity": 0.7} if area else {}

    if len(y_columns) == 1:
        return (
            alt.Chart(df).mark_circle()
            if mark_type == "scatter"
            else getattr(alt.Chart(df), f"mark_{mark_type}")(**mark_params).encode(
                x=get_formatted_axis(df, x_column),
                y=get_formatted_axis(df, y_columns[0], is_y_axis=True),
                tooltip=[x_column, y_columns[0]],
            )
        )

    melted_df = pd.melt(
        df,
        id_vars=[x_column],
        value_vars=y_columns,
        var_name="metric",
        value_name="value",
    )

    if all("distance" in y.lower() for y in y_columns):
        y_title = "Distance (km)"
    elif all(
        any(term in y.lower() for term in ["time", "elapsed", "moving"])
        for y in y_columns
    ):
        y_title = "Time"
        return (
            alt.Chart(melted_df).mark_circle()
            if mark_type == "scatter"
            else getattr(alt.Chart(melted_df), f"mark_{mark_type}")(
                **mark_params
            ).encode(
                x=get_formatted_axis(df, x_column),
                y=alt.Y(
                    "value:Q", title=y_title, axis=alt.Axis(labelExpr=TIME_FORMAT_EXPR)
                ),
                color="metric:N",
                tooltip=[x_column, "metric", "value"],
            )
        )
    else:
        y_title = "Value"

    return (
        alt.Chart(melted_df).mark_circle()
        if mark_type == "scatter"
        else getattr(alt.Chart(melted_df), f"mark_{mark_type}")(**mark_params).encode(
            x=get_formatted_axis(df, x_column),
            y=alt.Y("value:Q", title=y_title),
            color="metric:N",
            tooltip=[x_column, "metric", "value"],
        )
    )


def create_bar_chart(df: pd.DataFrame, x_column: str, y_column: str) -> alt.Chart:
    """Create a bar chart."""
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=get_formatted_axis(df, x_column),
            y=get_formatted_axis(df, y_column, is_y_axis=True),
            tooltip=[x_column, y_column],
        )
    )


def create_scatter_chart(df: pd.DataFrame, x_column: str, y_column: str) -> alt.Chart:
    """Create a scatter plot."""
    return (
        alt.Chart(df)
        .mark_circle()
        .encode(
            x=get_formatted_axis(df, x_column),
            y=get_formatted_axis(df, y_column, is_y_axis=True),
            tooltip=[x_column, y_column],
        )
    )


def create_pie_chart(df: pd.DataFrame, x_column: str, y_column: str) -> alt.Chart:
    """Create a pie chart for aggregate categorical data."""
    df_sorted = df.sort_values(by=y_column, ascending=False).reset_index(drop=True)
    total = df_sorted[y_column].sum()
    df_sorted['percentage'] = (df_sorted[y_column] / total * 100).round(1).astype(str) + '%'
    
    pie = alt.Chart(df_sorted).mark_arc().encode(
        theta=alt.Theta(field=y_column, type="quantitative"),
        color=alt.Color(field=x_column, type="nominal"),
        tooltip=[
            alt.Tooltip(field=x_column, type="nominal", title="Category"),
            alt.Tooltip(field=y_column, type="quantitative", title="Value"),
            alt.Tooltip(field="percentage", type="nominal", title="Percentage")
        ]
    )
    
    return pie.properties(width=400, height=400)


def display_visualization(chart: alt.Chart) -> None:
    """Display a visualization in Streamlit."""
    st.altair_chart(chart, use_container_width=True)
