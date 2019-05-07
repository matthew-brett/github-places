Contributions to scientific Python by country
=============================================

Do some countries contribute to the foundations of scientific Python more or
less than their fair share?

To answer this question, we need the countries for each significant contributor to the scientific Python foundation libraries.

We can find the significant contributors using a clone of the code repository, and the git `shortlog` command, that lists contributors by number of commits.

Github users often give some indication of where they live in the Location field of the Github profile, although not in a standard format.

To use the Github location data, we need to match contributors from `git shortlog` to the Github user profile.   This is not always easy, as the user's email may not be registered with Github, so we need to use heuristics to make a reliable guess, or fall back to old-fashioned web-stalking, to find who the person is, and match them with their Github profile, if any.
