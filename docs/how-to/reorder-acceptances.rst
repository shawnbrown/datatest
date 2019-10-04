
.. py:currentmodule:: datatest

.. meta::
    :description: How to re-order acceptances.
    :keywords: datatest, order of operations, acceptance, order


###########################
How to Re-Order Acceptances
###########################

Individual acceptances can be combined together to create new acceptances
with narrower or broader criteria (see :ref:`composability-docs`).
When acceptances are combined, their criteria are applied in an order
determined by their scope. Element-wise criteria are applied first,
group-wise criteria are applied second, and whole-error criteria are
applied last (see :ref:`order-of-operations-docs`).


Implicit Ordering
-----------------

In this first example, ``accepted([Missing('A'), ...])`` (a group-wise
acceptance) is applied first and ``accepted.count()`` (a whole-error
acceptance) is applied second::

    with accepted.count(4) | accepted([Missing('A'), Missing('B')]):
        ...


Explicit Ordering
-----------------

If you want to control this order explicitly, you can use nested
``with`` statements to change the default behavior::

    with accepted([Missing('A'), Missing('B')]):
        with accepted.count(4):
            ...

Using nested ``with`` statements, the inner-most block is applied
first and outer blocks are applied in order until the outer-most
block is applied last.
