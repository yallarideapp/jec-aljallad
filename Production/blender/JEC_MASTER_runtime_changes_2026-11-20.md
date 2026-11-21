# JEC_MASTER.blend — changes applied at runtime (saved in the .blend, not yet in jmbuild/jmroom.py)

## Fixes
- G_PlotDirt rendered pure black in stages 1-4 whenever G_FillBefore was hidden (Cycles quirk with the shared M_Dirt
  material). Fix: G_PlotDirt now uses its own copy, M_DirtPlot. S1-S4 re-rendered (final/ext).
- Pivot-door leaves E_DoorL/E_DoorR: thick refractive glass went black at grazing angles (transmission bounces).
  Now M_GlassThinDoor (Fresnel mix of transparent + glossy). Walk frames 120-196 re-rendered.
- Walk exposure keys (eye adaptation through the lobby): 1:0, 150:0, 160:0.8, 172:1.7, 186:2.3, 196:2.6, 248:2.6.
- Walk camera keys (north of column 3,-3; min clearance 0.51 m):
  (1,(-31,-47,18),(1.5,-1,11.5),25) (40,(-22.5,-40.5,11.5),(0.5,-4,8),26) (80,(-9.5,-31.5,4.4),(0,-8,4.2),25)
  (115,(-1.6,-22,1.8),(0,-9,2.6),24) (140,(0,-15.6,2.05),(0,-6,2.2),23) (160,(0,-11.3,2.0),(0,-3,2.0),22)
  (176,(0,-8.6,1.95),(0.2,-1,1.95),21) (196,(0.4,-5.6,1.9),(3.0,-1.2,1.9),20) (214,(1.6,-2.4,1.85),(8.0,-2.2,1.85),19)
  (230,(3.1,-2.05,1.82),(11.0,-3.5,1.9),18.5) (248,(4.4,-3.4,1.8),(14.6,-5.3,2.15),18)
- X-ray: R_CoveLight int=[7,10]; ceiling paint, cove, slots and downlight discs capped at int 10.

## Extra construction anchors (ext stage 3 with objects hidden)
- S2a: hide S_Beams1/2, S_Cols0/1, S_Core0/1, S_Slab1/2, S_Stair0/1, T_EdgeForm2, T_EdgeRail2, T_Props2(+Heads), T_StartersL2
- S2f: S2a + collection TMP_Formwork (TMP_ColForm plywood boxes at the 24 column positions + core, TMP_ColYokes)
- S2b: like S2a but S_Cols0, S_Core0, S_Stair0 visible
  (TMP_Formwork objects are tagged ext [99,100] but sit outside ROOT: hide them manually after set_state.)

## Higgsfield (flux_3_video, 1080p, 5 s, 24 fps native, start/end frames = Blender renders)
c20 S0>S1, c21 S1>S2, c28 S2>S2a (frames 79-120 used: the model cut to a close-up at 23-77), c29 S2a>S2f,
c30 S2f>S2b, c27 S2b>S3, c23 S3>S4, c24 S4>S5, c25 S5>S6, h10 duskA>duskB (hero), h11 S6>S7_dusk (end, first 7 frames cut).
Rejected: c22 S2>S3 (columns changed size/count), c26 S2>S2b (extra formwork boxes, then a jump), minimax_h3 and
gemini_omni_flash_1_2 tests (generation failed).
