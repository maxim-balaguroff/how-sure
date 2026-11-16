# What must the survey resolve?

English · [Русский](README.ru.md)

**A magnetic survey check for one geological question, before the survey is flown.**

For geologists who ask for a magnetic survey and then have to live with what it can and cannot show. Describe the body you need to see and the survey you have in mind; the page tells you whether the body will stand above the noise, whether two bodies will show as two, and how far apart the lines can be.

Why it matters in petroleum work: where igneous intrusions cut a sedimentary basin, dolerite sills and dykes blur the seismic image, can break up reservoirs and seals, and cause trouble while drilling. Magnetic data map them cheaply, before the wells are placed.

**[Open the page](https://maxim-balaguroff.github.io/how-sure/02-magnetic-survey-check/magnetic-survey-check.html)** · [download the file](https://github.com/maxim-balaguroff/how-sure/releases/latest/download/magnetic-survey-check.html) (one HTML file, works offline in any browser)

[![The page on its made-up example: a dyke 20 m wide, its top 300 m below ground, seen from 80 m](screenshot-page.png)](https://maxim-balaguroff.github.io/how-sure/02-magnetic-survey-check/magnetic-survey-check.html)

## What it tells you

- **Visible or not.** The peak anomaly of the body against the noise of the final data: clear at 5 × noise or more, marginal at 2 to 5 ×, lost under 2 ×. Also the highest sensor height at which the body stays clear.
- **One anomaly or two.** Whether a second body nearby shows as a separate peak, and below what sensor height the two come apart, if any.
- **Line spacing.** For a short body such as a plug: how much of its peak the nearest line still sees when the body falls midway between lines, and the widest spacing that keeps 70 %. For a dyke or a sill edge: lines within about 45° of perpendicular to strike cross it on every line, so the spacing decides how well the map follows it, not whether it is seen.
- **The same body at other heights.** A table for typical ground, low-clearance UAV, helicopter and fixed-wing heights, so the trade-off is on one screen.

## The example (made up)

A dolerite dyke 20 m wide, its top 300 m below ground, susceptibility contrast 0.02 SI, Earth's field 55,000 nT, noise 0.5 nT, sensor 80 m above ground. A second dyke runs 300 m away.

- The dyke gives 9.2 nT, 18 times the noise. It stays clear with the sensor up to about 1,100 m above ground.
- The two dykes show as one anomaly, and they stay one even with the sensor on the ground. Two thin bodies only split when they are more than about 1.15 times the sensor-to-top distance apart, and here that distance is already 302 m on the ground.
- From 150 m down to 2 m the peak grows only 1.5 times. Flying lower improves signal and resolution only as far as it shortens h; here h is mostly depth, so it buys little of either, and the two dykes stay one.

## How it works

For a body that runs a long way down, magnetised by a vertical field, the anomaly is proportional to the angle its top subtends at the sensor; for a plug, to the solid angle; for a sill edge, to the angle of its top minus the angle of its base. Depth and sensor height add up: what counts is h, the distance from the sensor to the top of the body. The 2D formulas are the textbook ones (Blakely, 1995).

Bodies: a vertical dyke of given width; the edge of a horizontal sill of given thickness; a plug as a vertical cylinder of given diameter.

Rules: the 5 × and 2 × thresholds and the 70 % rule for line spacing are my conventions. Reid (1980) gives up to about 2 h for a smooth total-field grid, about h for gradients and h/2 for a single point-like target (reviewed by Saltus, 2026). Two-body splitting is judged on a noise-free total-field profile that crosses both bodies; a vertical-derivative map can split them a little closer if the noise allows. For a sill edge the verdict uses the high on one side; the swing to the low beyond the edge is twice that, so the verdict errs on the safe side.

The height presets are typical starting values for ground, low-clearance UAV, helicopter and fixed-wing surveys. They are parameters, not a record of surveys flown. In a project, the geologist sets the question and interprets the data; a licensed contractor designs and flies the survey.

## Checked against known answers

The page carries 24 checks and shows the result at the bottom: **ALL 24 PASS** (checked in Microsoft Edge). Each check compares the page with an answer worked out another way:

- **by hand**, from textbook relations: a thin dyke's half-width at half peak equals h; in the infinite-depth model a very wide body tends to kF/2; two thin dykes merge below 1.155 h and two small plugs below h; a small plug midway between lines spaced h keeps 71.6 % of its peak, at 2 h 35.4 %;
- **by an independent sum** of elementary dipoles over the body's cross-section or volume ([`physics_ref.py`](physics_ref.py)), which does not use the page's closed forms but shares its model assumptions (vertical field, infinite depth, flat ground).

Change the code and break a formula, and a row turns FAIL.

## Limits

- Vertical field and induced magnetisation only. Outside high latitudes the raw anomaly of a long body is smaller by about sin²I + cos²I·sin²β (I inclination, β strike from magnetic north): 0.4 for a north-striking dyke at I = 40°, 0.03 at I = 10°. Reduction to the pole restores the shape but amplifies the noise by the same factor, so read the verdict as optimistic by that factor.
- No remanence; dolerites often carry it, and it can change the sign of the anomaly.
- Idealised bodies running to infinite depth: a dyke infinitely long, a straight sill edge, a plug as a vertical cylinder. A thin dyke whose base is b below the sensor gives about (1 − h/b) of the value shown, a thin plug about (1 − h²/b²); bodies wider than they are deep are overstated. The example dyke, if it ends 1 km below its top, gives about 28 % less.
- Flat ground and constant sensor height. In rugged terrain fixed-wing clearance over valleys is well above nominal.
- Noise is one number, the RMS of what is left after processing at wavelengths like the anomaly's: diurnal, heading and levelling errors and the geological and cultural background (pipelines, well casings) are assumed to be inside it. It is held the same at every height in the table, though ground and UAV data are often noisier.
- Ground readings are treated as continuous along the line; the station spacing is not checked.
- The page frames the question for a survey design. It does not replace the contractor's design.

## Files

| File | What it is |
|---|---|
| [`magnetic-survey-check.html`](magnetic-survey-check.html) | The page: one file, no internet needed, no data leaves the browser |
| [`physics_ref.py`](physics_ref.py) | Independent dipole sums behind the checks (Python, numpy) |
| `screenshot-page.png` | The page on its example |

References: Blakely, R. J. (1995). *Potential Theory in Gravity and Magnetic Applications*. Cambridge University Press. Reid, A. B. (1980). Aeromagnetic survey design. *Geophysics*, 45(5), 973–976. [doi:10.1190/1.1441102](https://doi.org/10.1190/1.1441102). Saltus, R. W. (2026). Evaluation of aliasing in aeromagnetic surveys: update to Reid 1980 analysis. *Earth and Space Science*. [doi:10.1029/2025EA004336](https://doi.org/10.1029/2025EA004336)

Built with AI assistance; the geology and the checks are mine.

Licence: [CC BY 4.0](../LICENSE). Maxim Balagurov, petroleum geologist · v1.1 · DOI [10.5281/zenodo.24242389](https://doi.org/10.5281/zenodo.24242389)
