
.. _existing stories: https://pulp.plan.io/issues?utf8=%E2%9C%93&set_filter=1&f%5B%5D=status_id&op%5Bstatus_id%5D=o&f%5B%5D=tracker_id&op%5Btracker_id%5D=%3D&v%5Btracker_id%5D%5B%5D=3&f%5B%5D=&c%5B%5D=project&c%5B%5D=tracker&c%5B%5D=status&c%5B%5D=priority&c%5B%5D=subject&c%5B%5D=assigned_to&c%5B%5D=updated_on&group_by=

New Features
============

All features are tracked in Redmine as an Story. You can view `existing stories`_ as examples.

Writing a Story
---------------

Writing a story is the first step towards new feature. You can `write a
new story <https://pulp.plan.io/projects/pulp/issues/new>`_ by selecting ``Story`` as the Tracker
type and giving an explanation of what the new feature will afford a user to do.

The first draft of the story is likely brief and is designed to facilitate discussion
with other users and developers. All discussion is captured as comments on the story.
A story that is ready will have the following items:

Title
  A clear name for the story. Typically something like: *As an <user type > I want
  <action phrase> so that <outcome phrase>*.

User Identification
  Who is the user? This could be a generic description, a user deploying Pulp,
  a user using Pulp, a user consuming content from Pulp, etc.

Context
  A brief description about what motivates this feature to exist.

Description
  Details and specifics about behaviors and names used with/by/for the feature.

Acceptance Criteria
  A set of pass/fail statements, each expressing a criteria of functional aspects
  of the feature. These are captured as checklists (an attribute on the ). This should
  include API specifications, CLI specifications, documentation needs, release note needs,
  testing criteria, or other deliverables that need to be completed to define what "done"
  looks like.

Once an author feels a story is ready, visit ``#pulp-dev`` and for a review of it. If
the reviewer agrees the story is ready, the reviewer marks the ``Groomed`` flag as
True. It is the author's responsibility to continue the conversation until the story is Groomed.


Sprint Candidate
----------------

An individual contributor is free to work on any story they wish, but for the core developers
we work in Sprints and any work to be done needs to be put on a Sprint.

An author who wishes to nominate their work to be included in a sprint should set the
``Sprint Candidate`` flag to True. The story must already be in a Groomed state before this
happens.


Adding Stories to Sprints
-------------------------

Stories picked by the core developers are discussed at a sprint planning meeting. If accepted,
the story is added to the next sprint.

If the story is not accepted onto the next sprint, the story has its ``Sprint Candidate`` boolean
set to False and must be re-nominated by the author for a later sprint.
