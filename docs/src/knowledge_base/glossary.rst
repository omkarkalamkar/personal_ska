=========
Glossary
=========

.. glossary::

    ProgramTrackTable

        The program track table in the SKA telescope system is a structured data set used to guide dish pointing during observations. It contains a sequence of future time-stamped entries specifying azimuth and elevation coordinates, allowing the Dish Manager to track a celestial source smoothly. 
        Typically, the Telescope Management Controller (TMC) provides 50(the number is configurable) such entries in advance, updating them at a configurable rate to maintain a moving time window. This mechanism ensures precise and continuous tracking, especially during dynamic operations like scans or non-sidereal observations.

        The detailed information is provided `here <https://confluence.skatelescope.org/x/VVILDw>`_.

    GlobalPointingModel, GPM

        A global pointing model(GPM) is a mathematical framework used to correct and improve the pointing accuracy of a telescope across the entire sky.
        In the context of the SKA (Square Kilometre Array) telescope, the global pointing model is built by analyzing pointing offset data—the difference between where the telescope is commanded to point and where it actually points.

        To know more about the GPM flow in TMC please click `here <https://confluence.skatelescope.org/x/V4TtEQ>`_.

        To know more about the contents in the GPM input json, please click `here <https://confluence.skatelescope.org/x/IojWE>`_.