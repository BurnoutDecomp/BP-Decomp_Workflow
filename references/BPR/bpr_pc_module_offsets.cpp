// BrnGame::BrnGameModule* gpBurnoutGame is at 0x013FC8E0
class BrnGame::BrnGameModule {
  /* 0x680 */    BrnRendererModule mRenderModule;
  /* 0x10A80 */  WorldModule mWorldModule;
  /* 0x61E180 */ BrnResource::GameDataModule mGameDataModule;
  /* 0x69B000 */ BrnGameState::GameStateModule mGameStateModule;
  /* 0x6EE700 */ BrnDirector::DirectorModule mDirectorModule;
  /* 0x71B820 */ CgsInput::InputModule mInputModule;
  /* 0x777E20 */ BrnGui::GuiModule mGuiModule;
  /* 0x9BB680 */ BrnEffects::EffectsModule mEffectsModule;
  /* 0xA06400 */ BrnSound::Module::RootSoundModule mSoundModule;
  /* Removed */  // BrnReplays::ReplayModule mReplayModule;
  /* 0xA1B300 */ BrnNetwork::BrnNetworkModule mNetworkModule;
};
class WorldModule {
  /* 0x280 */    BrnWorld::RaceCarEntityModule mRaceCarEntityModule;
  /* 0x37C80 */  BrnTraffic::TrafficEntityModule mTrafficEntityModule;
  /* 0xB0800 */  BrnWorld::WorldEntityModule mWorldEntityModule;
  /* 0xB6600 */  BrnWorld::PropEntityModule mPropEntityModule;
  /* 0x189980 */ BrnWorld::TriggerEntityModule mTriggerEntityModule;
  /* 0x18CBE0 */ UnknownModule mUnknownModule; // Added after 1.6 - runs global model dictionary
  /* 0x195C40 */ BrnPhysics::PhysicsModule mPhysicsModule;
  /* 0x214040 */ // Unknown
  /* 0x215480 */ CgsSceneManager::SceneManagerModule mSceneModule;
  /* 0x5BD780 */ BrnAI::AIModule mAIModule;
  /* 0x609790 */ BrnWorld::CrashModule mCrashModule;
};
class BrnWorld::WorldEntityModule {
  /* 0xA50 */ BrnWorld::PVSModule mPVSModule;
};
class BrnPhysics::PhysicsModule {
  /* 0x220 */ BrnPhysics::PhysicsSimulationModule mSimulationModule;
};
class CgsSceneManager::SceneManagerModule {
  /* 0x280 */   CgsSceneManager::OverlapGenerationModule mOverlapGenerator;
  /* 0xDC960 */ CgsSceneManager::OverlapCullingModule mOverlapCuller;
};
class BrnAI::AIModule {
  /* 0x44260 */ BrnAI::RouteMapModule mRouteMapModule;
};
class BrnResource::GameDataModule {
  /* 0x280 */   CgsResource::ResourceModule mResourceModule;
  /* 0x641D8 */ CgsAttribSys::AttribSysModule mAttribSysModule;
};
class CgsResource::ResourceModule {
  /* 0x280 */   CgsResource::BundleLoaderModule mBundleLoaderModule;
  /* 0x2E800 */ CgsResource::PoolModule mPoolModule;
  /* 0x49280 */ CgsMemory::MemoryModule mMemoryModule;
};
class BrnGui::GuiModule {
  /* 0x218 */   BrnGui::ModelModule mGuiModel;
  /* 0x20720 */ BrnGui::ViewModule mViewModule;
};
class BrnGui::ModelModule {
  /* 0x220 */   BrnGui::EventInterpreterModule mEventInterpreter;
  /* 0x18900 */ BrnGui::GuiResourceModule mGuiResource;
};
class BrnEffects::EffectsModule {
  /* 0xA80 */ BrnParticle::ParticleModule mParticleModule;
};
class BrnSound::Module::RootSoundModule {
  /* 0x280 */ BrnSound::Module::SoundLogicModule mLogicModule;
};
class BrnSound::Module::SoundLogicModule {
  /* 0x228 */ CgsSound::Playback::Module::Module mPlaybackModule;
};