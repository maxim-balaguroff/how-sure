# Five wells: which five? How the page works

English · [Русский](how-it-works.ru.md) · back to the [README](README.md)

The details behind the page: what it tells you, the made-up example in full, what the published campaign shows, how it counts, the rules, the checks and the limits.

## What it tells you

- **The best set.** Which sites to drill for the number of wells you have, found by scoring every set. The score adds points for each target unit cored and each horizon dated, weighted by priority; its top is what a campaign would score if it cored every target and dated every horizon for sure.
- **What each next well buys.** The best score for every number of wells, and which high-priority targets still rest on one hole.
- **Where each core lands.** For every site, the chance that the core holds enough of each unit to count it, and crosses each horizon with enough rock on both sides, within the errors of the pick, the dip, the cover and the unit thicknesses.
- **Dating.** A horizon counts as dated only if the rock on both sides gives an age. Each unit carries its own chance of that: high in marine mudstone and shale, low in red beds and clean sand.
- **Plan against fact, and what to drill next.** After a well is drilled, enter the unit identified in its core and the depth at which its anchor horizon was met. If the errors allow that core, the page narrows where the horizon can lie at the other sites that share its pick error and chooses the next wells again. If they do not, the horizon does not tie: the page says how far it would have to move, and holds the sites still to drill on it until it is re-picked.
- **The order, stand-ins and reserves.** Which well to drill first, second and so on, and whether stopping after any well (weather, time) leaves the best set for that number. For each planned site, the best stand-in if it cannot be drilled; the sites left out ranked by what they would add.
- **How firm the choice is.** The best set again if every hole delivered, with the 2D pick error halved or half as large again, and with nothing shared between the picks of one horizon; the sites that stay in every time.
- **High-res lines.** What a high-resolution line through every site would add before drilling.

## The example (made up)

Seven units, youngest first, with the chance that their core gives an age: fluvial red beds (120 m, 20 %), deltaic sandstone (90 m, reservoir, 60 %), marine mudstone (50 m, seal, 90 %), shoreface sandstone (80 m, reservoir, 70 %), organic-rich shale (40 m, source rock, 90 %), silty mudstone (140 m, seal, 90 %), basal sandstone (80 m, reservoir, 60 %). Twelve candidate sites, four of them on a high-res line. Each hole reaches 100 m below the seabed, and 80 % of holes bring back usable core. Pick error ±4 m on a high-res line and ±30 m on 2D only; 2D sites on one horizon share the side of the error, deeper or shallower than picked. Dip ±1°, cover ±4 m, unit thicknesses ±10 %. Chances below count the holes that fail, unless marked "if the hole delivers".

- **The best five are B, F, I, J and L, drilled in the order J, F, L, I, B.** They reach every high-priority unit and key boundary, though three of those targets (H3, H4 and the source rock) are under 90 % sure. They score 16.9 of a possible 23, coring 400 of the 500 m drilled.
- **What each next well buys.** Five wells take 85 % of what all twelve sites could give. The fifth adds 1.2 points, the sixth 0.8, the twelfth 0.1: six wells score 17.7 and all twelve 19.8. The source rock and key boundary H4 rest on site F alone; if F cannot be drilled, E is its best stand-in, and the score drops to 16.0.
- **Dating is the weak link.** On average 6.2 of 7 target units are cored, but only 2.6 of 6 boundaries dated. H4 is dated only 40 % of the time: the hole has to deliver, cross it, and both the sandstone above and the shale below have to give ages. H3 is 53 % from J and B together. Site I crosses H1 in every case, yet even when the hole delivers it dates H1 only 12 % of the time, because the red beds above rarely give ages.
- **A 2D pick can be a coin toss.** At site J, on 2D only, whether the core holds 5 m of the deltaic sandstone is 58 % if the hole delivers.
- **A horizon comes in deeper.** Press *Example with two made-up cores: a horizon comes in deeper*. The first well, J, is identified as the deltaic sandstone and meets H2 at 31 m, 13 m deeper than picked; the second, F, meets H4 4 m shallower. Both fit. J has cored the deltaic sandstone and crossed H2, so B, planned largely as its back-up, adds little; and with the side shared, H2 is taken to lie deeper at B as well, between 65 and 95 m and not 35 to 95 m, where B cannot reach H3. The fifth well changes: drill L, I and G next, not L, I and B. Counting what the cores showed, that scores 19.2 of 23, against 19.0 with the wells planned before. The main cause is the first: the fifth well would change even with nothing shared between the picks, or with H2 met exactly as picked; the shared side only widens the gap. Had H2 come in shallower than picked, B would have stayed in the plan.
- **A core does not tie.** Press *Example with two made-up cores: one does not tie*. The core at J is identified as the red beds, unit 1: H2 would have to lie at least 81 m deeper than the 18 m picked, against a pick error of ±30 m. Re-check the pick and the velocity there, or the core may be a younger fill the seismic does not separate. H2 does not tie, so B, the other site on H2, is held until the horizon is re-picked, and the next wells become C, I and L.
- **How firm the choice is.** If every hole delivered, or with the 2D pick at ±15 m or ±45 m, B drops out of the best five; F, J and L are in it every time. Those three are the firm picks to drill first. With nothing shared between the picks, the five stay the same, and the score moves by less than 0.1: with one hole in five failing, the back-ups guard against a lost hole more than against the pick.
- **High-res lines.** A high-res line through every site would lift the best five from 16.9 to 17.6 and change the choice to A, C, F, J and L. Every site gets a site survey for shallow hazards before drilling anyway, so the 2D picks are for choosing where to shoot it. The two made-up cores keep the 2D picks so that the numbers are large enough to see; on site-survey picks the same logic runs on a few metres.

## What the published campaign shows

The example is made up. These lines are from the paper on the real campaign (Malyshev et al., 2023, [doi:10.2113/RGG20224459](https://doi.org/10.2113/RGG20224459)), one for each finding.

- **Reserve sites were planned in.** Sites were chosen as principal and reserve ones, aiming at the widest stratigraphic range with wells shallower than 100 m. One of the ten wells was a reserve site, drilled during a storm mooring; it penetrated the same Upper Devonian unit as one of the principal wells.
- **Dating was the product.** Ages came from conodonts, fish remains, spores and other fossils; in well SSD 23 no macrofauna was encountered and the age came from palynology. The fossil ages moved two boundaries on the seismic: the Ordovician–Silurian boundary to an unconformity earlier taken to separate Silurian and Devonian, and the Silurian–Devonian boundary to near a horizon earlier read as lying inside the Lower Devonian. In well SSD 26 conodonts gave two ages within one carbonate unit, Middle to Upper(?) Ordovician and lower Silurian.
- **The plan changed as the campaign went.** The later sites were adjusted from new seismic rather than from cores: while one vessel drilled, a second shot ultrahigh-resolution seismic across the planned sites. Within a well, total depth and coring intervals were decided from the rock description sent from the site. Overall, the first results tend to make the section older than the base model implied.
- **For scale.** The wells were planned at about 100 m; the core is 298.4 m from ten wells, 80 % of the cumulative drilled depth; the ultrahigh-resolution survey is twelve lines, 298 km, with a vertical resolution of about 2.5 m.

## How it counts

- At each site the beds dip at one angle under a flat cover. A point z metres below the seabed lies (z<sub>H</sub> − z)·cos θ above the anchor horizon in the section, z<sub>H</sub> being the horizon's depth at the site and θ the dip. So the core, from the base of the cover q to the bottom of the hole D, spans (D − q)·cos θ of section, placed by the pick.
- For each site the page takes every combination of the errors: the pick error is integrated exactly, and the dip, the cover and the thickness (one factor for all units at a site) are stepped on a grid of 21 × 21 × 11. It counts how often the core holds the set length of each unit and the set rock on both sides of each horizon. A horizon's chance is then multiplied by the two units' chances of giving an age, and every chance by the share of holes that deliver.
- What the picks of one horizon share: the ± range is cut into equal parts, two when they share the side. Which part the true depth lies in is the same for all sites anchored on that horizon and picked on the same kind of seismic (2D only, or a high-res line); where it lies inside the part is each site's own. So each site's error stays spread evenly over its ±, and two such wells hit and miss together more often than two wells on different horizons.
- The score of a set of wells adds, for each unit, its priority (high 3, medium 2, low 1) times the chance that at least one well cores it, and for each horizon its value (key 2, useful 1) times the chance that at least one well dates it. Wells on different horizons count as independent; holes fail and rocks give ages independently everywhere.

## Rules

- **Best set:** every set of the chosen size is scored and the best kept; on equal scores, the set that cores more metres, then the first found.
- **Order:** each next well is the one that adds most to the wells already drilled. This does not guarantee that every early stop leaves the best set for that number, so the page checks it and says how close it comes; in the example it is the best set every time.
- **Verdict:** sure when every high-priority unit and key boundary is at least 90 % likely; thin when one of them is under 90 %; short when a high-priority unit is under 60 %, a medium one under 30 %, or a key boundary under 30 %. One hole alone gives a target at most the share of holes that deliver, so 90 % usually takes two holes on it.
- **After drilling:** a unit identified in a core fits the plan if the errors can put it in the core at least one time in five; unlikely if less; no fit if never. A horizon met in the core fits if its depth lies within the pick error.
- **What to drill next:** where the errors allow what a core showed, each part of the pick range is weighted by how well it allows it; that narrows where the horizon can lie at the other sites that share its pick error. An unlikely core is still used, and marked. Where nothing allows it, the horizon does not tie: all its sites still to drill are held, and the drilled well counts the unit identified only. The wells still to drill are then chosen again on top of the wells drilled; a drilled hole has delivered, and the unit identified in it counts as cored.

## Checked against hand calculations and an independent count

The page carries 49 checks and shows the result at the bottom: **ALL 49 PASS**. Each check compares the page with an answer worked out another way:

- **by hand**, from the geometry: where a core sits in the section and how long it is, the chance of crossing a horizon on a pick error alone, the cases with no errors where a horizon is crossed or a unit is in the core or not, a horizon dated with ages from 90 % and 70 % of cores (0.63), a hole that stops in the cover, the score of two holes on one unit on different horizons and on the same one (they hit together, or one covers for the other), the top score of the example, the metres of a unit at one site, the shift of the anchor horizon a core calls for, and after drilling what one core says about the other site on its horizon: the side it now lies on, the weights of the two sides, and a site held where the horizon does not tie;
- **by an independent count** ([`sites_ref.py`](sites_ref.py)). It does not integrate: it draws two million random combinations of the errors for the sites on each horizon and counts the cores, then searches every set of wells by the rules above. After drilling it keeps the draws that agree with the made-up cores and chooses the next wells again. Chances must agree within 0.005 and scores within 0.02; the best set, the drilling order, the first reserve, the first stand-in, the best set with a high-res line at every site, the best sets of the firmness test, the wells to drill next and the site held must be the same.

The checks test the arithmetic, not the geology or the error ranges. Change the code and break a formula, and a row turns FAIL.

## Limits

- The example is made up. One dip per site, no faults between the core and its anchor horizon, a flat base to the cover. Faults repeat or cut out section; anchor on a horizon on the same side of any fault.
- Errors are spread evenly over their ± ranges (take each as the largest plausible error), so "always" and "never" mean within the ranges entered. Picking the wrong reflector lies outside any ± range: the page sees it only after drilling, as a core that does not tie.
- After drilling the page knows only the unit identified and the depth of one horizon at each site. It cannot re-pick a horizon: that takes the seismic and the whole core description. Re-run the plan with the site-survey picks before drilling, and with the new picks after any re-tie.
- What the picks of one horizon share is a rough model. Only the part of the range carries over from a core to the other sites, not the size of the miss: a 1 m miss and a 25 m miss narrow them alike. Sites on a high-res line and sites on 2D only do not inform each other, and an error common to all horizons, one velocity model for the whole area, is not in it.
- A core that does not tie may put the neighbouring horizons in doubt too; the page holds only the sites on that one.
- The pick error grows with the anchor's depth through the velocity, and a site off the seismic line adds the offset times the tangent of the dip: enter both in the pick error.
- A hole either delivers or not. In practice holes also stop early on boulders or refusal, deeper targets and thick glacial cover carry more of that risk, and core is lost most at contacts, where dating needs rock.
- The dip, cover and thickness errors are stepped on a grid that stops a few percent short of the ends of their ranges, so "nothing within the errors" can miss the outermost corner.
- Rock 30–100 m below the seabed can be weathered, glacially deformed or a rafted block, and its porosity, seal quality and maturity differ from the same unit at depth.
- The ages come from the laboratory, often months after the campaign; on the vessel the unit is first told from the rock itself. The page checks the unit against the pick, not the dating. Each site must clear a shallow gas and seabed hazard check and keep off mapped closures. Nothing here on cost, vessels, weather or permits.

Built with AI assistance; the geology and the checks are mine.
