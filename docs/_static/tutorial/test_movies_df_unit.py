#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import datatest as dt


def setUpModule():
    global df
    with dt.working_directory(__file__):
        df = pd.read_csv('movies.csv')


class TestMovies(dt.DataTestCase):
    @dt.mandatory
    def test_columns(self):
        self.assertValid(
            df.columns,
            {'title', 'rating', 'year', 'runtime'},
        )

    def test_title(self):
        self.assertValidRegex(df['title'], r'^[A-Z]')

    def test_rating(self):
        self.assertValidSuperset(
            df['rating'],
            {'G', 'PG', 'PG-13', 'R', 'NC-17', 'Not Rated'},
        )

    def test_year(self):
        self.assertValid(df['year'], int)

    def test_runtime(self):
        self.assertValid(df['runtime'], int)
