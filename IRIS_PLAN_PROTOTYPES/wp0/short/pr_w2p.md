`world2pixel_single_axis` keeps only the world inputs directly correlated with the requested pixel axis and collapses the others to their first element. Inverting pixel axis x of a cube whose celestial axes depend on (x, y, t) needs the time value per element, so world-coordinate links into such a WCS (an IRIS SJI gWCS, for example) were evaluated at the first exposure: derived x for three frames came out as [21.05, 144.96, 275.06] where the direct inverse gives [21.05, 20.62, 21.24].

The needed world axes are now the transitive closure over shared pixel axes. Test: a synthetic two-pixel-axis WCS whose longitude depends on both axes.

Label: bug.
