# CAR PRODUCE ONE — scroll-linked prototype

Copy: `app/content.ts`. Camera timeline and decoder controller: `app/journey-timeline.ts`.

## Interaction contract
- Native document scroll is the only camera clock. The introductory scroll space spans 12 small viewport heights; wheel, scrollbar, keyboard and touch all use the same document offset.
- `sampleJourney(scrollY / scrollSpaceHeight)` determines video time, camera hold, city dissolve and portal reveal. Camera footage is always paused and sought to that time. There is no play-to-next-stop behavior and no timed entry into the main site.
- Each camera movement can stop or reverse at any scroll position. Returning upward from the beginning of the main site restores the portal at the matching progress.
- Tools, magazines and monitor reading ranges use independent stationary-camera ambient loops. Their camera positions stay fixed regardless of waiting time. Background pause affects those loops and the city loop only.
- Decoder seeks coalesce to the latest scroll target, including reversals during a pending seek. `journey-scrub.mp4` has all 720 frames independently decodable.
- Chapter buttons jump the actual document scroll position. Direct service/contact links skip to the main content. Replay returns to the city.
- Portal geometry and HTML opacity derive from scroll. Only the brief 160ms noise pulse decays by elapsed time. The reveal and main site share one hero component.

## Validation
7 Node regression tests cover partial movement, stopping, reversal, holds, decoder backpressure, loading and endpoint bounds. TypeScript, production build and local HTTP response are checked. Browser interaction/visual testing has not been performed in this pass.

## Media limits
The existing 640x360, 8fps review frames are retained. Camera-seek format and three short stationary-camera loops are newly encoded from them. Production resolution, portrait camera composition, window-only city transition masks and exact monitor corner tracking remain media/design refinements. Mobile shows the complete landscape image with letterboxing. QR is unchanged from the user-provided image.

Business facts and omissions follow the supplied stage 1 copy. This is the existing owner-private Sites preview, not the official public launch.
