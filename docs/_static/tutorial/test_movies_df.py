#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
import pandas as pd
import datatest as dt


@pytest.fixture(scope='module')
@dt.working_directory(__file__)
def df():
    return pd.read_csv('movies.csv')


@pytest.mark.mandatory
def test_columns(df):
    dt.validate(
        df.columns,
        {'title', 'rating', 'year', 'runtime'},
    )


def test_title(df):
    dt.validate.regex(df['title'], r'^[A-Z]')


def test_rating(df):
    dt.validate.superset(
        df['rating'],
        {'G', 'PG', 'PG-13', 'R', 'NC-17', 'Not Rated'},
    )


def test_year(df):
    dt.validate(df['year'], int)


def test_runtime(df):
    dt.validate(df['runtime'], int)
