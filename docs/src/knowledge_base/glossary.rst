=========
Glossary
=========

.. glossary::

    ProgramTrackTable

        The program track table in the SKA telescope system is a structured data set used to guide dish pointing during observations. It contains a sequence of future time-stamped entries specifying azimuth and elevation coordinates, allowing the Dish Manager to track a celestial source smoothly. 
        Typically, the Telescope Management Controller (TMC) provides 50(the number is configurable) such entries in advance, updating them at a configurable rate to maintain a moving time window. This mechanism ensures precise and continuous tracking, especially during dynamic operations like scans or non-sidereal observations.

        The detailed information is provided `here <https://confluence.skatelescope.org/x/VVILDw>`_.