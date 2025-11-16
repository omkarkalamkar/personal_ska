=========
Glossary
=========

.. glossary::

    ProgramTrackTable

        The program track table in the SKA telescope system is a structured data set used to guide dish pointing during observations. It contains a sequence of future time-stamped entries specifying azimuth and elevation coordinates, allowing the Dish Manager to track a celestial source smoothly. 
        Typically, the Telescope Management Controller (TMC) provides 50(the number is configurable) such entries in advance, updating them at a configurable rate to maintain a moving time window. This mechanism ensures precise and continuous tracking, especially during dynamic operations like scans or :term:`Non-SiderealTracking`.

        The detailed information is provided `here <https://confluence.skatelescope.org/x/VVILDw>`_.

    GlobalPointingModel
    GPM

        A global pointing model(GPM) is a mathematical framework used to correct and improve the pointing accuracy of a telescope across the entire sky.
        In the context of the SKA (Square Kilometre Array) telescope, the global pointing model is built by analyzing pointing offset data—the difference between where the telescope is commanded to point and where it actually points.

        To know more about the GPM flow in TMC please follow `this <https://confluence.skatelescope.org/x/V4TtEQ>`_.

        To know more about the contents in the GPM input json, please `click <https://confluence.skatelescope.org/x/IojWE>`_.

    Non-SiderealTracking

        Non-sidereal tracking enables a telescope to follow celestial bodies that move independently of the fixed star background—such as the Moon, Sun, planets, or artificial satellites. Unlike sidereal tracking, which relies on Earth's rotation to maintain alignment with distant stars, non-sidereal tracking demands real-time adjustments to accommodate the unique motion of these dynamic targets.

        In the configuration JSON, this mode is indicated by setting the reference_frame to "special" and specifying the target_name as one of the supported solar system objects (e.g., Moon, Sun, Mercury, Venus). Based on these inputs, the Telescope Management Controller (TMC) initiates the generation of a program track table tailored to the selected non-sidereal target.
        For more information please go through the `ADR-63 <https://confluence.skatelescope.org/x/VVILDw>`_.

    HolographyPatterns

        Holography in the SKA telescope context refers to a specialized mapping pattern used for precise measurements, particularly in calibration and beam characterization. Unlike standard mapping techniques, holography involves a tailored scan trajectory—often defined by complex patterns like "raster"—executed by a subset of receptors while another group remains fixed on the target source. This dual-group configuration allows for detailed spatial sampling of the beam response. The implementation and requirements for holography are being refined under `ADR-94 <https://confluence.skatelescope.org/x/nPJcE>`_, with future developments expected to formalize its design and integration into the control data model.

        For more details about mapping scan, please go through `ADR-63`_ and `ADR-94`_.

        The Mapping scan flow in TMC is explained on this `page <https://confluence.skatelescope.org/x/E0OzEQ>`_.