Original route-menu map opacity: source check

ARTIST OnlineSelectRoute::ShowMainMenu stores zero to its map active byte at 0x82493114..18. ShowSelectCheckpointMenu stores zero to the same byte at 0x82493278. The owned MainMapComponent starts at OnlineSelectRoute+0x51F0 and the active byte is component+0x67C = +0x586C. ShowPresetEvents stores one there at 0x82493414/6C. Current named SetActive(false/true) calls preserve these transitions.

The original MainMapRenderer::RenderComponent 0x82460188..1A4 uses alpha128 when the delivered active byte is false and no fade is in progress; an active map or an in-progress fade instead uses its animated alpha. Thus a settled half-transparent map while the route-options menu has focus matches the original behavior. This is distinct from the recovered missing start-marker branches and does not explain the user's whole-game freeze. No force-opaque patch is proposed.

This source check extends the already-reviewed event/alpha producer chain. Earlier5093 direct frames showed opaque preset selection and half opacity after Back; the new candidate's pixels remain pending. No debug site credit or complete freeze resolution is claimed.
