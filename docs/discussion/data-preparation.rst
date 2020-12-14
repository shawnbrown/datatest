
.. meta::
    :description: A discussion about the need for a structured approach
                  to data preparation and data-wrangling.
    :keywords: data preparation, test driven, data-wrangling, structured,
               data science


################
Data Preparation
################

.. epigraph::

    *"Hell is other people's data."*
    ---Jim Harris [#f1]_


In the practice of data science, data preparation is a huge part of
the job. Practitioners often spend 50 to 80 percent of their time
wrangling data [#f2]_ [#f3]_ [#f4]_ [#f5]_.  This critically important
phase is time-consuming, unglamorous, and often poorly structured.

The :mod:`datatest` package was created to support test driven
data-wrangling and provide a disciplined approach to an otherwise
messy process.

A datatest suite can facilitate quick edit-test cycles to help guide
the selection, cleaning, integration, and formatting of data. Data tests
can also help to automate check-lists, measure progress, and promote
best practices.


**************************
Test Driven Data-Wrangling
**************************

.. epigraph::

    *"...tidy datasets are all alike but every messy dataset is messy
    in its own way"*
    ---Hadley Wickham [#f6]_


When data is messy, poorly structured, or uses an incompatible format,
it's oftentimes not possible to prepare it using an automated process.
There are a multitude of ways for messy data to counfound a processing
system or schema. Dealing with data like this requires a data-wrangling
approach where users are actively involved with making decisions and
judgment calls about cleaning and formatting the data.

A well-structured suite of data tests can serve as a template to guide
the data-wrangling process. Using a quick edit-test cycle, users can:

 1. focus on a failing test
 2. make change to the data or the test
 3. re-run the suite to check that the test now passes
 4. then, move on to the next failing test

The work of cleaning and formatting data takes place outside of the
datatest package itself.  Users can work with with the tools they find
the most productive (Excel, `pandas <http://pandas.pydata.org/>`_, R,
sed, etc.).


.. rubric:: Footnotes

.. [#f1] Harris, Jim. "Hell is other people’s data", OCDQ (blog), August 06, 2010,
         Retrieved from http://www.ocdqblog.com/home/hell-is-other-peoples-data.html

.. [#f2] "Data scientists, according to interviews and expert estimates, spend
         from 50 percent to 80 percent of their time mired in this more mundane
         labor of collecting and preparing unruly digital data..." Steve Lohraug
         in *For Big-Data Scientists, 'Janitor Work' Is Key Hurdle to Insights*.
         Retrieved from http://www.nytimes.com/2014/08/18/technology/for-big-data-scientists-hurdle-to-insights-is-janitor-work.html

.. [#f3] "This [data preparation step] has historically taken the largest part
         of the overall time in the data mining solution process, which in some
         cases can approach 80% of the time." *Dynamic Warehousing: Data Mining
         Made Easy* (p. 19)

.. [#f4] Online poll of data mining practitioners: `See image <../_static/data_prep_poll.png>`_,
        *Data preparation (Oct 2003)*.
        Retrieved from http://www.kdnuggets.com/polls/2003/data_preparation.htm
        [While this poll is quite old, the situation has not changed
        drastically.]

.. [#f5] "As much as 80% of KDD is about preparing data, and the remaining 20%
         is about mining." *Data Mining for Design and Manufacturing* (p. 44)

.. [#f6] Wickham, Hadley. "Tidy Data." Journal of Statistical Software 59,
         no. 10, August 2014.
