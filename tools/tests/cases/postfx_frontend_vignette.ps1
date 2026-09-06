# postfx_frontend_vignette -- BurnoutDecomp/b5-decomp#4 "PostFX: effects appear on top of
# the startup UI".
#
# THE BUG, stated as a number. The boot autosave prompt is 2D drawn AFTER the post-fx
# composite (console Render @0x8240BFA8: BrnPostFx::Render -> LoadingScreenRenderer::
# RenderBackground -> the GUI -> RenderForeground), so the prompt itself is never
# post-processed -- but the picture BEHIND it is, and on this build the base effects
# layer hands the composite a VIGNETTE whose outer colour is a dark blue
# (0.0549, 0.2078, 0.3765). The composite's last colour op is
#   rgb = composite * lerp(inner, outer, smoothstep(saturate(radius + gradientAdd)))
# so the whole boot picture is multiplied by that: dark, and blue far out of proportion
# to anything in the scene. That is what the report's screenshot shows.
#
# The console does NOT apply it. EffectsModule::GenerateRenderRequests @0x8227FF10 writes
# the base layer's VignetteData with VignetteData::Construct(frame+0x40, hash64("198102"))
# and asset "198102" is in no shipped collection, so the vignetteasset ctor @0x82677F70
# falls through to Attrib::DefaultDataArea(0x50) @0x821F0048 -- 0x1D48 bytes that are ALL
# ZERO in the image. A zeroed vignette is inner == outer == 0 and the base layer stops
# contributing anything until the environment timeline's world layer replaces it.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case postfx_frontend_vignette -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case postfx_frontend_vignette -Label post-fix
@{
  Name         = 'postfx_frontend_vignette'
  Area         = 'graphics/postfx'
  Bug          = 'BurnoutDecomp/b5-decomp#4 -- PostFX (a dark-blue vignette) washes the boot/autosave-prompt screen'
  # NO FRAME DUMP. The picture cannot arbitrate this bug on this build's boot: the base
  # vignette only multiplies what the WORLD pass drew, and between the loading screen, the
  # title art and the black transitions the world is never visible behind the front end in a
  # dumped frame -- measured over run 20260906_100220's 66 frames, whose two world-only sample
  # regions read either 0.0 luminance or the 2D loading art's own blue sky (b/r 2.29 on the
  # ARTWORK, i.e. the same signature the vignette would leave). The number the bug moves is the
  # vignette the composite multiplies by, and the witness below prints it where the console
  # computes it. Frames are still available from that run for eyeballing.
  Frames       = $false
  # ⛔ NOT FreshProfile. The boot-up autosave warning is posted on EVERY boot
  # (SaveLoadSystem::BootupShowAutosaveWarning @0x828599A0 is the bootup path, not a
  # first-boot one -- the returning-player boot loads SaveLoadComponent.bundle and posts
  # loading-screen command 138 exactly the same way). And the FreshProfile path is broken
  # on this build for reasons that have nothing to do with post-fx: it access-violates in
  # MainGameFlowStateInitialLoadingScreen::Update ~3.4 s in, writing 0x000000000000A0DD,
  # right after "[GameStateModule::Prepare] stage 26 ... prepare DONE" (measured
  # 2026-09-06, run 20260906_095423). Reported separately; using the ordinary boot keeps
  # this case measuring post-fx.
  FreshProfile = $false
  Run          = @{
    MaxSeconds = 45             # boot only: the front-end vignette is applied from the first frame
  }
  # BRN_POSTFX_DIAG lights the [postfx] vignette witness (BrnRendererModulePostFx.cpp,
  # on-change only, capped at 24 lines).
  DiagEnv      = 'BRN_POSTFX_DIAG=1'
  Checks       = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }

    # THE WITNESS. The first vignette the composite ever applies is the base layer's (the
    # world layer contributes nothing until the environment timeline is up -- see the
    # [postfx-fx] apply-call samples). Console: all zeros. This build: outer.b = 0.3765,
    # VignetteData::kv4DefOuterColour, the "environment disabled" fallback seed.
    @{ Kind = 'LogValue'; Name = 'first applied vignette outer.b is the console zero'
       Pattern = '\[postfx\] vignette apply \d+: active=1 .*outer=\([-\d.]+,[-\d.]+,(?<b>[-\d.]+)\)'
       Group = 'b'; Agg = 'first'; Min = -0.02; Max = 0.02 }
    @{ Kind = 'LogValue'; Name = 'first applied vignette outer.r is the console zero'
       Pattern = '\[postfx\] vignette apply \d+: active=1 .*outer=\((?<r>[-\d.]+),'
       Group = 'r'; Agg = 'first'; Min = -0.02; Max = 0.02 }

  )
}
