# Component manager usability (found by Beaux, 2026-11-20)

Beaux used the 0.4.0 windows by hand and listed what got in the way. Each
item below was checked against the code (what the code does today is stated
in each task). Rules for all of them: invented test data only; keep logic in
plain functions that CI can test, because CI opens no window (T-047 changes
that); say in the task what it adds to the executable and confirm the CI size
numbers (see Size gate); and finish with a short hand check on Windows. The
decision in the 2026-11-17 Decision log still holds: **the app carries no
built-in schemas for kinds of contract**, so "preset" fields below means the
publisher-profile fields the app already has plus fields the user defines.

Suggested order: T-040, T-044, T-041, T-045 are quick and independent. T-047
makes the rest easier to prove. T-043 comes before T-046 (they share storage).
T-042 starts with a decision from Beaux. T-048 (the start screen) can go
anytime after T-040. T-049 and the publisher type in T-046-C need the field
store of T-043-A. These ship after 0.4.1 (T-039) as 0.5.0.
