###########################
Contributing
###########################

MUIOGO is an open-source project, and contributions are welcome.

The most useful contributions are clear, scoped, and grounded in the current
direction of the repository. Before proposing implementation work, take time to
understand what the project is trying to do, what already exists, and how your
proposal fits the current priorities.

Getting Started
---------------------------

Start with the repository documentation:

* ``README.md``
* ``CONTRIBUTING.md``
* ``SUPPORT.md``
* ``docs/ARCHITECTURE.md``
* ``docs/DOCS_POLICY.md``

These documents are the source of truth for the contributor workflow.

Code Contributions
-------------------

MUIOGO uses an issue-first, discussion-before-PR workflow for most
implementation work.

Before writing code:

1. Search existing issues, pull requests, and discussions.
2. Create or reuse an issue before starting implementation work.
3. Describe the current problem, relevant related work, and why the issue is
   still needed.
4. Confirm the scope before opening a large implementation PR.
5. Create a feature branch from ``main`` for the implementation.

Why this matters:

* it reduces duplicate or overlapping work
* it helps maintainers keep review effort focused on current priorities
* it makes it easier to discuss tradeoffs before code is written

MUIOGO is downstream from ``OSeMOSYS/MUIO``. Contributors should avoid creating
unnecessary divergence from upstream when a narrower or more compatible change
would do the job.

Documentation Contributions
-------------------

Documentation improvements are welcome, including:

* clarifying setup steps
* fixing outdated or misleading instructions
* improving architecture or workflow explanations
* adding missing validation or troubleshooting details

Any setup, workflow, or architecture change should update the relevant
documentation in the same pull request.

Examples and Use Cases
-------------------

Examples, demo improvements, and real-world use cases can be helpful when they
make the project easier to understand or test.

If you want to contribute an example:

1. Explain what the example demonstrates.
2. Keep it small enough to be practical for review and reuse.
3. Include a short README or description covering the purpose, assumptions, and
   any data-source constraints.
4. Open or link an issue first if the example changes tracked project scope,
   demo assets, or contributor workflow.

Communication
-------------------

Good communication is part of the contribution.

Strong contributions usually include:

* a concrete problem statement
* a scoped proposal
* links to related work already reviewed
* clear validation steps
* direct explanations of tradeoffs or upstream-compatibility impact

Questions are welcome. It is especially helpful when questions include enough
context to make them easy to answer and act on.
