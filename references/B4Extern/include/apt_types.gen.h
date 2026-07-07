// AUTO-GENERATED from Burnout Revenge B4Extern.pdb (Apt 0.19.02, Xenon/PPC).
// REFERENCE ONLY -- version-drift vs Paradise Apt (2008). Do NOT compile into
// b5-decomp/src. Raw ground truth: ../pdb-dump/. Regenerate with
// tools/apt_revenge/generate_apt_headers.py . Layouts are 32-bit (4-byte ptr).
#pragma once

// 151 Apt types, 838 methods.

struct AptActionInterpreter;
struct AptFrame;
struct AptMovie;
struct AptCharacterGlyphEntry;
struct AptControlDoInitAction;
struct AptImport;
struct AptControlFrameLabel;
struct AptExport;
struct AptControlDoAction;
struct AptConstantTable;
struct AptEventActionBlock;
struct AptCharacterStaticTextRecords;
class AptMouse;
class AptValueGC_PoolManager;
class AptValueVector;
struct AptPseudoCIH_t;
struct AptCharacterShapeInst;
class AptNativeFunction;
class AptSound;
class AptBasePtrStack<AptValue>;
struct AptCharacterAnimation;
struct AptCharacterText;
struct AptControlBackgroundColour;
struct AptConstantPool;
class AptValueGlobalWithHash;
class AptFrameStack;
class AptMath;
struct AptMath::Vec4_t;
struct AptMath::Mat44_t;
struct AptControl;
class AptError;
struct AptCharacterAnimationInst;
struct AptFile;
struct AptSysClock;
struct AptCharacterSprite;
class AptNativeHash;
class AptActionQueueC;
struct AptActionQueueC::AptActionPool;
struct AptActionQueueC::AptFunction;
struct AptActionQueueC::AptAction;
class AptMovieClip;
class AptScriptFunction1;
class AptSharedPtr<AptFile>;
struct AptValue::<unnamed-tag>::<unnamed-tag>;
class AptValue;
class AptScriptFunctionBase;
struct AptLinkerThingy;
class AptSharedPtr<AptLinkerThingy>;
class AptFloat;
struct AptnCXForm;
struct AptActionSetup;
struct AptCharacterButtonInst;
class AptExtObject;
class AptGlobal;
class AptGlobalExtensionObject;
struct AptControlPlaceObject2;
struct AptAnalogStickInfo;
struct AptSingleListPolicy;
class AptScriptColour;
class AptValuePtrStack<AptValue>;
struct AptPseudoData_t;
struct AptSharedPtrRefCount;
class AptXmlNode;
class AptString;
class AptXmlAttributePair;
struct AptCXForm;
struct AptCharacterMorphInst;
struct AptAction_DefineFunction;
struct AptRegisterParam;
struct AptCharacterFont;
struct AptFileSavedInputState;
class AptValueGC;
class AptPseudoDisplayList;
class AptMathObj;
struct AptMemoryAllocationsT;
class AptTextFormat;
struct AptCharacterSpriteInst;
struct AptCharacterStaticText;
struct AptConstFile;
class AptExtern;
struct AptCharacter;
class AptBoolean;
struct AptAllocateStringParameters;
struct AptCharacterBitmap;
class AptArray;
struct AptRect;
class AptCIH;
class AptValueNoGC;
struct AptHashItem;
class AptLookup;
class AptLoadVars;
struct AptControlRemoveObject2;
class AptDate;
struct AptLoader;
class AptStringObject;
class AptPrototype;
class AptKey;
struct AptSavedInputRecord;
struct AptMatrix;
struct AptLinker;
class AptXml;
class AptXmlAttributes;
struct AptIntervalTimer;
struct AptMovieclipInformation;
struct AptAction_TryCatchFinallyBlock;
struct AptAction_DefineFunction2;
struct AptSavedInputCheckpoints;
struct AptActionBlock;
class AptInteger;
struct AptDisplayListState;
class AptRegister;
class AptScriptFunctionByteCodeBlock;
struct AptCharacterMorph;
class AptValueWithHash;
struct AptCharacterTextInst;
class AptStage;
struct AptCharacterStaticTextInst;
class AptNone;
struct AptAnimationPoolData;
struct AptInitParmsT;
struct AptCharacterInst;
class AptObject;
struct AptDisplayList;
class AptScriptFunction2;
struct AptActionInterpreter::FunctionTable;
struct AptActionInterpreter::LocalContextT;
struct AptUserFunctions;
struct AptSavedInputRecordCustom;
struct AptSavedInputRecordInput;
class AptFastStack;
struct AptActionInterpreter::_FunctionAptActionPushStringDictWord::__l2::<unnamed-tag>::<unnamed-tag>;
union AptActionInterpreter::_FunctionAptActionPushStringDictWord::__l2::<unnamed-tag>;
struct AptActionInterpreter::_FunctionAptActionPushFloat::__l2::<unnamed-tag>::<unnamed-tag>;
union AptActionInterpreter::_FunctionAptActionPushFloat::__l2::<unnamed-tag>;
struct AptActionInterpreter::_FunctionAptActionPushWord::__l2::<unnamed-tag>::<unnamed-tag>;
union AptActionInterpreter::_FunctionAptActionPushWord::__l2::<unnamed-tag>;
struct AptActionInterpreter::_FunctionAptActionPushDWord::__l2::<unnamed-tag>::<unnamed-tag>;
union AptActionInterpreter::_FunctionAptActionPushDWord::__l2::<unnamed-tag>;
struct AptAction_GotoFrame2;
struct AptAction_PushString;
struct AptAction_With;
struct AptAction_GotoFrame;
struct AptAction_Push;
struct AptAction_SetTarget;
struct AptAction_StoreRegister;
struct AptAction_BranchAddress;
struct AptAction_GetUrl;
struct AptAction_GotoLabel;
struct AptRenderingContext;
struct AptSavedInputRecordCheckpoint;
class AptValueFactory;

// ---- AptActionInterpreter  (sizeof = 96) ----
struct AptActionInterpreter {
    /* +0x00 */ AptBasePtrStack<AptValue> stack;
    /* +0x0c */ AptValuePtrStack<AptValue> withStack;
    /* +0x18 */ AptValuePtrStack<AptValue> setTargetStack;
    /* +0x24 */ AptValuePtrStack<AptValue> thisStack;
    /* +0x30 */ AptScriptFunctionBase* mpCurrentFunction;
    /* +0x34 */ AptConstantPool constantPool;
    /* +0x3c */ unsigned int input;
    /* +0x40 */ AptValue* apRegisters[4];
    /* +0x50 */ int nThisCount;
    /* +0x54 */ AptValue* mpThrownValue;
    /* +0x58 */ int mnStackFrameBase;
    /* +0x5c */ bool bShutDown;
    // --- methods (address @ B4Extern) ---
    // 0x828C78: AptValue* __cdecl AptActionInterpreter::stackGetPop()
    // 0x828C98: void __cdecl AptActionInterpreter::stackPushIndirect(const AptValue* pValue)
    // 0x828DA8: void __cdecl AptActionInterpreter::stackPush(const AptValue* pValue)
    // 0x828DE0: void __cdecl AptActionInterpreter::stackPushNoInc(const AptValue* pValue)
    // 0x828E00: void __cdecl AptActionInterpreter::stackPopNoDec()
    // 0x828E18: void __cdecl AptActionInterpreter::stackPopAndPush(int nCountToPop, const AptValue* pValue)
    // 0x828788: void __cdecl AptActionInterpreter::stackPop()
    // 0x828E20: void __cdecl AptActionInterpreter::stackPop(const int nItems)
    // 0x828E28: void __cdecl AptActionInterpreter::stackSafePop(const int nItems)
    // 0x836560: virtual bool __cdecl AptActionInterpreter::getContext(AptValue* pCurrentContext, AptValue* pWith, EAStringC* pVarName, AptValue** ppContext, char* szName) = 0
    // 0x8367A8: virtual AptValue* __cdecl AptActionInterpreter::cbCallMethod_ASSetPropFlags(AptValue* pContext, int nParams) = 0
    // 0x836A20: virtual void __cdecl AptActionInterpreter::getName2(AptCIH* pCIH, EAStringC& sBuf) = 0
    // 0x836B68: virtual void __cdecl AptActionInterpreter::getName(AptCIH* pCIH, EAStringC& sBuf) = 0
    // 0x836C20: void* __cdecl AptActionInterpreter::PrepareForExecution(const char* pszLocationinfo)
    // 0x836C28: void* __cdecl AptActionInterpreter::PrepareForExecution(AptActionSetup* pActionSetup)
    // 0x836C30: void __cdecl AptActionInterpreter::CleanupAfterExecution(const char* pszLocationinfo, void* pPassedValue)
    // 0x836D00: void __cdecl AptActionInterpreter::CleanupAfterExecution(void* pPassedValue, AptActionSetup* pActionSetup)
    // 0x837128: const char* __cdecl AptActionInterpreter::urlDecode(const char* szURL, EAStringC& sKey, EAStringC& sValue)
    // 0x837278: bool __cdecl AptActionInterpreter::isFSCommand(const char* szCommand)
    // 0x8372D0: int __cdecl AptActionInterpreter::doFSCommand(const char* szCommand, const char* szParams)
    // 0x837338: virtual void __cdecl AptActionInterpreter::_FunctionAptActionEnd(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837340: virtual void __cdecl AptActionInterpreter::_FunctionAptActionNextFrame(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837390: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPrevFrame(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8373E0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionToggleQuality(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8373E8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStopSounds(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8373F0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStopDragMovie(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837470: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStringLessThan(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837478: virtual void __cdecl AptActionInterpreter::_FunctionAptActionMBLength(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837480: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCharToAscii(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837488: virtual void __cdecl AptActionInterpreter::_FunctionAptActionMBSubString(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837490: virtual void __cdecl AptActionInterpreter::_FunctionAptActionMBCharToAscii(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837498: virtual void __cdecl AptActionInterpreter::_FunctionAptActionMBAsciiToChar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8374A0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionReturn(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8374B0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBitURShift(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8374B8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGetUrl(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8376B8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDefineDictionary(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8376E8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionWaitForFrame(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8376F0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGotoLabel(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x837810: virtual bool __cdecl AptActionInterpreter::isObjectOfType(AptValue* pObject, AptValue* pInterface) = 0
    // 0x837A00: void __cdecl AptActionInterpreter::initialize(AptInitParmsT& aptInitParms)
    // 0x837A98: void __cdecl AptActionInterpreter::shutdown()
    // 0x837B68: virtual bool __cdecl AptActionInterpreter::getContext(AptValue* pCurrentContext, AptValue* pWith, EAStringC* pVarName, AptValue** ppContext, EAStringC& sName) = 0
    // 0x837CF0: virtual AptValue* __cdecl AptActionInterpreter::cbCallMethod_clearInterval(AptValue* pContext, int nParams) = 0
    // 0x837DD8: virtual AptValue* __cdecl AptActionInterpreter::cbCallMethod_unescape(AptValue* pContext, int nParams) = 0
    // 0x837FC0: virtual AptValue* __cdecl AptActionInterpreter::cbCallMethod_escape(AptValue* pContext, int nParams) = 0
    // 0x838178: AptValue* __cdecl AptActionInterpreter::getVariable(AptValue* pCurrentContext, AptValue* pWith, EAStringC* pVarName, int bGlobal, int bLookInFunctionScope, int bIsMember)
    // 0x838798: void __cdecl AptActionInterpreter::_doEnumerate(AptValue* pCurrentContext, AptValue* pCurWith)
    // 0x838D78: const unsigned char* __cdecl AptActionInterpreter::runStream(const unsigned char* aActionStream, AptCIH* pCurrentContext, int nMaxStreamBytes, AptCharacterInst* pParentCharacter)
    // 0x839030: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPlay(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x839180: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStop(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x839210: virtual void __cdecl AptActionInterpreter::_FunctionAptActionSubString(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x839560: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPop(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8395F8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGetVariable(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x839750: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStringAdd(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x839958: virtual void __cdecl AptActionInterpreter::_FunctionAptActionTrace(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x839BA8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStartDragMovie(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x839EC0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionAsciiToChar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83A140: virtual void __cdecl AptActionInterpreter::_FunctionAptActionInitArray(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83A250: virtual void __cdecl AptActionInterpreter::_FunctionAptActionTypeOf(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83A748: virtual void __cdecl AptActionInterpreter::_FunctionAptActionEnumerate(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83A758: virtual void __cdecl AptActionInterpreter::_FunctionAptActionToString(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83AB20: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushDuplicate(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83AB58: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStackSwap(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83ABC8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGetMember(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83AEF0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionEnumerate2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83AF00: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGotoFrame(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83B048: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStoreRegister(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83B078: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPush(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83B1B0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBranchIfTrue(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83B270: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCallFrame(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83B440: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGotoFrame2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83B768: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBranchAlways(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83B7B8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushThis(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83B918: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushGlobal(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BA78: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushNULL(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BAB0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushUndefined(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BAE8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushThisVariable(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BB60: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushGlobalVariable(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BB98: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushString(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BD40: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushStringDictByte(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BD90: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushStringDictWord(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BE10: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushStringGetVar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83BF20: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushStringGetMember(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83C0D8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStringDictByteGetVar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83C180: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStringDictByteGetMember(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83C208: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBranchIfFalse(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83C2C8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCastOp(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83C3C8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionThrow(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x83C460: virtual void __cdecl AptActionInterpreter::_parseStream(unsigned char* aActionStream, unsigned char* pBase, AptConstFile* aConstantFile, int* pnCurrentConstantIndex) = 0
    // 0x83CFE8: virtual void __cdecl AptActionInterpreter::unresolveStream(unsigned char* aActionStream, unsigned char* pBase, int* pnCurrentConstantIndex) = 0
    // 0x83CFF8: virtual void __cdecl AptActionInterpreter::resolveStream(unsigned char* aActionStream, unsigned char* pBase, AptConstFile* aConstantFile, int* pnCurrentConstantIndex) = 0
    // 0x83D000: virtual AptValue* __cdecl AptActionInterpreter::getObject(AptValue* pCurrentContext, AptValue* pWith, EAStringC* pPathName) = 0
    // 0x83D160: virtual AptValue* __cdecl AptActionInterpreter::cbCallMethod_setInterval(AptValue* pContext, int nParams) = 0
    // 0x83D638: virtual AptValue* __cdecl AptActionInterpreter::cbCallMethod_hitTest(AptCIH* pCIH, int nParams) = 0
    // 0x83D880: virtual AptValue* __cdecl AptActionInterpreter::cbCallMethod_isNaN(AptValue* pContext, int nParams) = 0
    // 0x83DFA8: virtual AptValue* __cdecl AptActionInterpreter::cbCallMethod_boolean(AptValue* pContext, int nParams) = 0
    // 0x83EBC8: virtual void __cdecl AptActionInterpreter::valueToObject(AptValue* pCurrentContext, AptValue* pWith, AptValue* pVal, AptValue** ppInst) = 0
    // 0x83ECE8: void __cdecl AptActionInterpreter::callFunction(AptValue* pContext, AptValue* pFuncDef, int nStackParams)
    // 0x83F128: AptObject* __cdecl AptActionInterpreter::_createObject(AptValue* pCurrentContext, AptValue* pCurWith, EAStringC* szObject, int nParams, bool bRunConstructor)
    // 0x83FF20: virtual void __cdecl AptActionInterpreter::_FunctionAptActionAdd(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x840330: virtual void __cdecl AptActionInterpreter::_FunctionAptActionSubtract(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x840740: virtual void __cdecl AptActionInterpreter::_FunctionAptActionMultiply(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x840B50: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDivide(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x840DC8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionEquals(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x841200: virtual void __cdecl AptActionInterpreter::_FunctionAptActionLessThan(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x841628: virtual void __cdecl AptActionInterpreter::_FunctionAptActionAnd(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x841A68: virtual void __cdecl AptActionInterpreter::_FunctionAptActionOr(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x841EA8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionNot(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x842068: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStringEquals(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8424F0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStringLength(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8426F8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionToInteger(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8428F8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionSetTarget2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x842A30: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGetProperty(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x842BD8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionRemoveSprite(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x842D00: virtual void __cdecl AptActionInterpreter::_FunctionAptActionRandom(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x842F00: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGetTimer(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x843078: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCallFunction(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8432B0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionModulo(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x843530: virtual void __cdecl AptActionInterpreter::_FunctionAptActionNewObject(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8436B8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionInitObject(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8438A8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionTargetPath(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x843BF0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionAdd2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8445E0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionLessThan2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x845390: virtual void __cdecl AptActionInterpreter::_FunctionAptActionEquals2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x846C88: virtual void __cdecl AptActionInterpreter::_FunctionAptActionToNumber(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x847540: virtual void __cdecl AptActionInterpreter::_FunctionAptActionIncrement(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8478B0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDecrement(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x847C20: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCallMethod(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x848750: virtual void __cdecl AptActionInterpreter::_FunctionAptActionNewMethod(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x848920: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBitAnd(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x848B08: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBitOr(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x848CF0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBitXor(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x848ED8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBitLShift(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8490C0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionBitRShift(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x8492A8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionStrictEquals(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x849960: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGreater(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x849D98: virtual void __cdecl AptActionInterpreter::_FunctionAptActionSetTarget(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x849EE8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionWith(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x849FD8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPush0(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84A150: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPush1(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84A2C8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushTrue(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84A440: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushFalse(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84A5B8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCallFuncAndPop(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84A640: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCallMethodPop(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84A6C8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDictCallFuncPop(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84A7B0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDictCallMethodPop(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84A898: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushFloat(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84AA50: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushByte(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84ABD8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushWord(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84AD78: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushDWord(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84AF30: virtual void __cdecl AptActionInterpreter::_FunctionAptActionExtends(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84B1E8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionInstanceOf(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84B378: virtual void __cdecl AptActionInterpreter::_FunctionAptActionImplementsOp(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84B650: bool __cdecl AptActionInterpreter::setVariable(AptValue* pCurrentContext, AptValue* pWith, EAStringC* pVarName, AptValue* pValue, int bGlobal, int bLookInFunctionScope, int bIsMember)
    // 0x84BBC0: AptValue* __cdecl AptActionInterpreter::_doCloneSprite(AptCIH* pCurrentCIH, AptValue* pWith, AptValue* pSource, AptValue* pTarget, int nDepthInt, AptValue* pInitObject)
    // 0x84BE48: virtual void __cdecl AptActionInterpreter::_FunctionAptActionSetVariable(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84BF70: virtual void __cdecl AptActionInterpreter::_FunctionAptActionSetProperty(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84C068: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCloneSprite(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84C120: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDelete(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84C388: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDelete2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84C5C8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDefineLocal(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84C6D8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDefineLocal2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84C868: virtual void __cdecl AptActionInterpreter::_FunctionAptActionSetMember(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84CCE8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDefineFunction(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84CE98: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDefineFunction2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84CFD0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCallFuncSetVar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84D038: virtual void __cdecl AptActionInterpreter::_FunctionAptActionCallMethodSetVar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84D0A0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushZeroSetVar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84D230: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushStringSetVar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84D3E8: virtual void __cdecl AptActionInterpreter::_FunctionAptActionPushStringSetMember(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84D5A0: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDictCallFuncSetVar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84D658: virtual void __cdecl AptActionInterpreter::_FunctionAptActionDictCallMethodSetVar(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84D710: virtual void __cdecl AptActionInterpreter::_FunctionAptActionTry(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x84D9B8: void __cdecl AptActionInterpreter::loadVariables(AptValue* pContext, AptValue* pWith, EAStringC* pURL)
    // 0x84DC90: virtual void __cdecl AptActionInterpreter::_FunctionAptActionGetUrl2(const AptActionInterpreter* pInterpreter, const AptActionInterpreter::LocalContextT* pLocalContext) = 0
    // 0x835FF0: bool __cdecl AptActionInterpreter::doUnwindStack()
    // 0x836010: void __cdecl AptActionInterpreter::throwValue(AptValue* pThrown)
    // 0x84E708: void __cdecl AptActionInterpreter::~AptActionInterpreter()
};
// static_assert(sizeof(AptActionInterpreter) == 96);  // 32-bit console layout

// ---- AptFrame  (sizeof = 8) ----
struct AptFrame {
    /* +0x00 */ int nControls;
    /* +0x04 */ AptControl** apControls;
};
// static_assert(sizeof(AptFrame) == 8);  // 32-bit console layout

// ---- AptMovie  (sizeof = 12) ----
struct AptMovie {
    /* +0x00 */ int nFrames;
    /* +0x04 */ AptFrame* aFrames;
    /* +0x08 */ AptNativeHash* phLabels;
    // --- methods (address @ B4Extern) ---
    // 0x87DDA0: void __cdecl AptMovie::unresolve(unsigned char* pBase, int* pnCurrentConstantIndex)
    // 0x87E0C8: void __cdecl AptMovie::DoTemporaryFrameControls(AptPseudoDisplayList* pPseudoDisplayList, int nFrame)
    // 0x87E2E8: void __cdecl AptMovie::doFrameControls(AptDisplayList* pDisplayList, AptCIH* pInst, int nFrame)
    // 0x87E498: void __cdecl AptMovie::runFrameActions(AptCIH* pInst, int nFrame)
    // 0x87E560: int __cdecl AptMovie::labelToFrame(EAStringC* pLabel)
    // 0x87E5A8: void __cdecl AptMovie::queueFrameActions(AptCIH* pInst, int nFrame)
    // 0x87E638: void __cdecl AptMovie::resolve(unsigned char* pBase, AptConstFile* aConstantFile, int* pnCurrentConstantIndex)
};
// static_assert(sizeof(AptMovie) == 12);  // 32-bit console layout

// ---- AptCharacterGlyphEntry  (sizeof = 4) ----
struct AptCharacterGlyphEntry {
    /* +0x00 */ short nIndex;
    /* +0x02 */ short nAdvance;
};
// static_assert(sizeof(AptCharacterGlyphEntry) == 4);  // 32-bit console layout

// ---- AptControlDoInitAction  (sizeof = 8) ----
struct AptControlDoInitAction {
    /* +0x00 */ int nSpriteID;
    /* +0x04 */ AptActionBlock actions;
};
// static_assert(sizeof(AptControlDoInitAction) == 8);  // 32-bit console layout

// ---- AptImport  (sizeof = 16) ----
struct AptImport {
    /* +0x00 */ char* szFile;
    /* +0x04 */ char* szName;
    /* +0x08 */ int nID;
    /* +0x0c */ AptSharedPtr<AptFile> file;
};
// static_assert(sizeof(AptImport) == 16);  // 32-bit console layout

// ---- AptControlFrameLabel  (sizeof = 4) ----
struct AptControlFrameLabel {
    /* +0x00 */ char* szLabel;
};
// static_assert(sizeof(AptControlFrameLabel) == 4);  // 32-bit console layout

// ---- AptExport  (sizeof = 8) ----
struct AptExport {
    /* +0x00 */ char* szName;
    /* +0x04 */ int nID;
};
// static_assert(sizeof(AptExport) == 8);  // 32-bit console layout

// ---- AptControlDoAction  (sizeof = 4) ----
struct AptControlDoAction {
    /* +0x00 */ AptActionBlock actions;
};
// static_assert(sizeof(AptControlDoAction) == 4);  // 32-bit console layout

// ---- AptConstantTable  (sizeof = 8) ----
struct AptConstantTable {
    /* +0x00 */ AptVirtualFunctionTable_Indices eType;
    /* +0x04 */ char* szString;
    /* +0x04 */ float fFloat;
    /* +0x04 */ int nInteger;
    /* +0x04 */ int nRegister;
    /* +0x04 */ int bBoolean;
    /* +0x04 */ unsigned int nLookup;
};
// static_assert(sizeof(AptConstantTable) == 8);  // 32-bit console layout

// ---- AptEventActionBlock  (sizeof = 12) ----
struct AptEventActionBlock {
    /* +0x00 */ int nTriggers;
    /* +0x04 */ int nKeyCode;
    /* +0x08 */ AptActionBlock actions;
};
// static_assert(sizeof(AptEventActionBlock) == 12);  // 32-bit console layout

// ---- AptCharacterStaticTextRecords  (sizeof = 56) ----
struct AptCharacterStaticTextRecords {
    /* +0x00 */ int nFontID;
    /* +0x04 */ AptCXForm cxform;
    /* +0x24 */ float fXOffset;
    /* +0x28 */ float fYOffset;
    /* +0x2c */ float fScale;
    /* +0x30 */ int nGlyphs;
    /* +0x34 */ AptCharacterGlyphEntry* aGlyphs;
};
// static_assert(sizeof(AptCharacterStaticTextRecords) == 56);  // 32-bit console layout

// ---- AptMouse  (sizeof = 32) ----
class AptMouse : public AptObject {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptMouse) == 32);  // 32-bit console layout

// ---- AptValueGC_PoolManager  (sizeof = 32) ----
class AptValueGC_PoolManager : public DOGMA_PoolManager {
    // --- methods (address @ B4Extern) ---
    // 0x824088: void __cdecl AptValueGC_PoolManager::AptValueGC_PoolManager(unsigned int mainPoolSizeBytes, unsigned int overflowPoolSizeBytes)
    // 0x82A948: AptValueGC* __cdecl AptValueGC_PoolManager::AllocateAptValueGC(unsigned int nAllocatedSize)
    // 0x82A9A8: void __cdecl AptValueGC_PoolManager::DeallocateAptValueGC(AptValueGC* pNowFree, unsigned int nAllocatedSize)
    // 0x82AA28: AptValue* __cdecl AptValueGC_PoolManager::GetNextAptValue(AptValue* pPrevious)
    // 0x82AC60: AptValue* __cdecl AptValueGC_PoolManager::GetFirstAptValue()
    // 0x82AD38: void __cdecl AptValueGC_PoolManager::VerifyList()
    // 0x82AD80: virtual void __cdecl AptValueGC_PoolManager::StaticInitialize() = 0
};
// static_assert(sizeof(AptValueGC_PoolManager) == 32);  // 32-bit console layout

// ---- AptValueVector  (sizeof = 12) ----
class AptValueVector {
    /* +0x00 */ int mCapacity;
    /* +0x04 */ int mCurrentNum;
    /* +0x08 */ AptValue** mpValues;
    // --- methods (address @ B4Extern) ---
    // 0x861758: void __cdecl AptValueVector::AptValueVector(const int iSize)
    // 0x8617B0: void __cdecl AptValueVector::~AptValueVector()
    // 0x8617D0: void __cdecl AptValueVector::ReleaseValues()
    // 0x824AE0: AptValue* __cdecl AptValueVector::GetAt(const int iPos)
    // 0x824AF0: void __cdecl AptValueVector::SetAt(const int iPos, AptValue* pVal)
    // 0x824B00: void __cdecl AptValueVector::RemoveAt(const int iPos)
    // 0x825190: AptValue* __cdecl AptValueVector::PopValue()
    // 0x8251B0: int __cdecl AptValueVector::GetNumValues()
    // 0x8251B8: int __cdecl AptValueVector::IsVectorFull()
};
// static_assert(sizeof(AptValueVector) == 12);  // 32-bit console layout

// ---- AptPseudoCIH_t  (sizeof = 20) ----
struct AptPseudoCIH_t {
    /* +0x00 */ AptControl* pControl;
    /* +0x04 */ AptPseudoData_t* pControlInfo;
    /* +0x08 */ AptPseudoCIH_t* pNext;
    /* +0x0c */ AptPseudoCIH_t* pPrev;
    /* +0x10 */ int nDepth;
    // --- methods (address @ B4Extern) ---
    // 0x875688: void __cdecl AptPseudoCIH_t::AptPseudoCIH_t(AptControl* pNewControl, int nFrame, int nDpth, AptCharacter* pNewCharacter)
};
// static_assert(sizeof(AptPseudoCIH_t) == 20);  // 32-bit console layout

// ---- AptCharacterShapeInst  (sizeof = 24) ----
struct AptCharacterShapeInst : public AptCharacterInst {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptCharacterShapeInst) == 24);  // 32-bit console layout

// ---- AptNativeFunction  (sizeof = 36) ----
class AptNativeFunction : public AptObject {
    /* +0x20 */ AptValue*  (__cdecl * pFunc)(AptValue*, int);
};
// static_assert(sizeof(AptNativeFunction) == 36);  // 32-bit console layout

// ---- AptSound  (sizeof = 32) ----
class AptSound : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x828BB8: virtual void __cdecl AptSound::~AptSound()
};
// static_assert(sizeof(AptSound) == 32);  // 32-bit console layout

// ---- AptBasePtrStack<AptValue>  (sizeof = 12) ----
class AptBasePtrStack<AptValue> {
    /* +0x00 */ int m_nElements;
    /* +0x04 */ int m_nCapacity;
    /* +0x08 */ AptValue** m_aElements;
};
// static_assert(sizeof(AptBasePtrStack<AptValue>) == 12);  // 32-bit console layout

// ---- AptCharacterAnimation  (sizeof = 52) ----
struct AptCharacterAnimation : public AptCharacterSprite {
    /* +0x0c */ int nCharacters;
    /* +0x10 */ AptCharacter** apCharacters;
    /* +0x14 */ unsigned int nWidth;
    /* +0x18 */ unsigned int nHeight;
    /* +0x1c */ unsigned int nMillisecondsPerFrame;
    /* +0x20 */ int nImports;
    /* +0x24 */ AptImport* aImports;
    /* +0x28 */ int nExports;
    /* +0x2c */ AptExport* aExports;
    /* +0x30 */ int nCurrentConstantIndex;
    // --- methods (address @ B4Extern) ---
    // 0x85EA38: int __cdecl AptCharacterAnimation::UnmapCharacter(AptCharacter* pCharacter)
    // 0x85EA78: int __cdecl AptCharacterAnimation::IsImport(int nID)
    // 0x85EC18: void __cdecl AptCharacterAnimation::ExportClassDefinitionAssets(AptCIH* pInst)
    // 0x85F2D0: void __cdecl AptCharacterAnimation::Link(AptCharacter* pParentAnim, void* pUserData)
    // 0x85FAB8: int __cdecl AptCharacterAnimation::GetIDFromImportFile(int nID)
    // 0x85FB48: void __cdecl AptCharacterAnimation::ExecuteInitAction(AptCIH* pInst, int nID)
    // 0x860210: void __cdecl AptCharacterAnimation::Fixup(void* pAptData, AptConstFile* pConstFile, void* pUserData)
    // 0x860610: void __cdecl AptCharacterAnimation::Resolve(void* pAptData, AptConstFile* pConstFile, void* pUserData)
    // 0x860670: void __cdecl AptCharacterAnimation::Unresolve(void* pAptData)
    // 0x8612E0: void __cdecl AptCharacterAnimation::ExecuteInitActions(AptCIH* pInst, int nID)
};
// static_assert(sizeof(AptCharacterAnimation) == 52);  // 32-bit console layout

// ---- AptCharacterText  (sizeof = 52) ----
struct AptCharacterText {
    /* +0x00 */ AptRect rBounds;
    /* +0x10 */ int nFontID;
    /* +0x14 */ AptStringAlignment eAlignment;
    /* +0x18 */ unsigned int nColour;
    /* +0x1c */ float fFontHeight;
    /* +0x20 */ int bReadOnly;
    /* +0x24 */ int bMultiLine;
    /* +0x28 */ int bWordWrap;
    /* +0x2c */ char* szInitialText;
    /* +0x30 */ char* szVariable;
};
// static_assert(sizeof(AptCharacterText) == 52);  // 32-bit console layout

// ---- AptControlBackgroundColour  (sizeof = 4) ----
struct AptControlBackgroundColour {
    /* +0x00 */ unsigned int nColour;
};
// static_assert(sizeof(AptControlBackgroundColour) == 4);  // 32-bit console layout

// ---- AptConstantPool  (sizeof = 8) ----
struct AptConstantPool {
    /* +0x00 */ int nItems;
    /* +0x04 */ AptValue** apItems;
};
// static_assert(sizeof(AptConstantPool) == 8);  // 32-bit console layout

// ---- AptValueGlobalWithHash  (sizeof = 28) ----
class AptValueGlobalWithHash : public AptValueWithHash {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptValueGlobalWithHash) == 28);  // 32-bit console layout

// ---- AptFrameStack  (sizeof = 32) ----
class AptFrameStack : public AptValueWithHash {
    /* +0x1c */ AptFrameStack* mpParentScope;
    // --- methods (address @ B4Extern) ---
    // 0x825238: void __cdecl AptFrameStack::Set(const EAStringC* pKey, const AptValue* pValue)
    // 0x825240: AptValue* __cdecl AptFrameStack::Lookup(const EAStringC* pKey)
    // 0x8247D8: void __cdecl AptFrameStack::ClearScope()
    // 0x7C9D90: void __cdecl AptFrameStack::GetHashSize()
    // 0x8247E0: bool __cdecl AptFrameStack::ExistsInLocalScope(EAStringC* pVarName)
    // 0x825238: void __cdecl AptFrameStack::SetInLocalScope(EAStringC* pVarName, AptValue* pValue)
    // 0x824818: bool __cdecl AptFrameStack::SetWhereExistsInScopeChain(EAStringC* pVarName, AptValue* pValue)
    // 0x824880: AptValue* __cdecl AptFrameStack::GetInScopeChain(EAStringC* pVarName)
    // 0x8294A8: void __cdecl AptFrameStack::AptFrameStack(AptFrameStack* pParentScope)
    // 0x829598: virtual void __cdecl AptFrameStack::DestroyGCPointers()
    // 0x8295E8: virtual void __cdecl AptFrameStack::RegisterReferences()
    // 0x8296E0: void __cdecl AptFrameStack::AptFrameStack(AptFrameStack* pParentScope, int nHashSize)
};
// static_assert(sizeof(AptFrameStack) == 32);  // 32-bit console layout

// ---- AptMath  (sizeof = 1) ----
class AptMath {
    /* +0x00 */ AptMath::Mat44_t Pos44;
    /* +0x40 */ AptMath::Vec4_t vColorMul4;
    /* +0x50 */ AptMath::Vec4_t vColorAdd4;
    // --- methods (address @ B4Extern) ---
    // 0x824100: virtual AptMath::ClipTransform_t* __cdecl AptMath::ClipStackPush() = 0
    // 0x824130: virtual AptMath::ClipTransform_t* __cdecl AptMath::ClipStackPop() = 0
    // 0x824168: virtual AptMath::ClipTransform_t* __cdecl AptMath::ClipStackGetTop() = 0
    // 0x824190: virtual bool __cdecl AptMath::ClipStackIsEmpty() = 0
    // 0x8241A8: virtual void __cdecl AptMath::MatMul2d(AptMath::Mat44_t* pOut, AptMath::Mat44_t* pA, AptMath::Mat44_t* pB) = 0
    // 0x824278: virtual void __cdecl AptMath::MatConvert(AptMath::Mat44_t* pAptMat44, AptMatrix* pAptMat) = 0
    // 0x85D5B8: virtual void __cdecl AptMath::ClipStackMakeUnit() = 0
    // 0x85D6B0: virtual void __cdecl AptMath::ClipStackPushUnit() = 0
    // 0x85D6C8: virtual void __cdecl AptMath::ClipStackInit(unsigned int nMaxTransforms) = 0
    // 0x85D750: virtual void __cdecl AptMath::ClipStackShutdown() = 0
};
// static_assert(sizeof(AptMath) == 1);  // 32-bit console layout

// ---- AptMath::Vec4_t  (sizeof = 16) ----
struct AptMath::Vec4_t {
    /* +0x00 */ float vx;
    /* +0x04 */ float vy;
    /* +0x08 */ float vz;
    /* +0x0c */ float vw;
};
// static_assert(sizeof(AptMath::Vec4_t) == 16);  // 32-bit console layout

// ---- AptMath::Mat44_t  (sizeof = 64) ----
struct AptMath::Mat44_t {
    /* +0x00 */ float m[16];
};
// static_assert(sizeof(AptMath::Mat44_t) == 64);  // 32-bit console layout

// ---- AptControl  (sizeof = 64) ----
struct AptControl {
    /* +0x00 */ AptControlType eType;
    /* +0x04 */ AptControlDoAction action;
    /* +0x04 */ AptControlDoInitAction initAction;
    /* +0x04 */ AptControlFrameLabel frameLabel;
    /* +0x04 */ AptControlPlaceObject2 placeObject2;
    /* +0x04 */ AptControlRemoveObject2 removeObject2;
    /* +0x04 */ AptControlBackgroundColour backgroundColour;
};
// static_assert(sizeof(AptControl) == 64);  // 32-bit console layout

// ---- AptError  (sizeof = 40) ----
class AptError : public AptObject {
    /* +0x20 */ EAStringC msMessage;
    /* +0x24 */ EAStringC msName;
    // --- methods (address @ B4Extern) ---
    // 0x84F1C8: void __cdecl AptError::AptError()
    // 0x84F328: void __cdecl AptError::AptError(EAStringC* sMessage)
    // 0x862820: virtual bool __cdecl AptError::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue)
    // 0x8629D0: virtual void __cdecl AptError::CleanNativeFunctions() = 0
    // 0x862D50: virtual void __cdecl AptError::~AptError()
    // 0x862DF8: virtual AptValue* __cdecl AptError::sMethod_toString(AptValue* pThis, int nParams) = 0
    // 0x867910: virtual AptValue* __cdecl AptError::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
};
// static_assert(sizeof(AptError) == 40);  // 32-bit console layout

// ---- AptCharacterAnimationInst  (sizeof = 56) ----
struct AptCharacterAnimationInst : public AptCharacterSpriteInstBase {
    /* +0x30 */ unsigned int nLeftoverTime;
    /* +0x34 */ AptSharedPtr<AptFile> pFile;
    // --- methods (address @ B4Extern) ---
    // 0x85EAC0: virtual void __cdecl AptCharacterAnimationInst::PreDestroy()
    // 0x85F2A0: int __cdecl AptCharacterAnimationInst::getSwfVersion()
    // 0x860C68: void __cdecl AptCharacterAnimationInst::AptCharacterAnimationInst(AptSharedPtr<AptFile>* file)
    // 0x860CF8: virtual void __cdecl AptCharacterAnimationInst::~AptCharacterAnimationInst()
};
// static_assert(sizeof(AptCharacterAnimationInst) == 56);  // 32-bit console layout

// ---- AptFile  (sizeof = 24) ----
struct AptFile : public AptSharedPtrRefCount {
    /* +0x04 */ EAStringC mName;
    /* +0x08 */ AptFile::State mState;
    /* +0x0c */ void* mAptData;
    /* +0x10 */ AptCharacter* mCharacter;
    /* +0x14 */ void* mUserData;
    // --- methods (address @ B4Extern) ---
    // 0x861498: AptCharacter* __cdecl AptFile::FindExport(const char* szName)
    // 0x8541B8: void __cdecl AptFile::~AptFile()
    // 0x854598: int __cdecl AptFile::isFileImported(AptSharedPtr<AptFile>* pFile)
};
// static_assert(sizeof(AptFile) == 24);  // 32-bit console layout

// ---- AptSysClock  (sizeof = 32) ----
struct AptSysClock {
    /* +0x00 */ int Second;
    /* +0x04 */ int Minute;
    /* +0x08 */ int Hour;
    /* +0x0c */ int Day;
    /* +0x10 */ int Date;
    /* +0x14 */ int Month;
    /* +0x18 */ int Year;
    /* +0x1c */ int Hundredths;
};
// static_assert(sizeof(AptSysClock) == 32);  // 32-bit console layout

// ---- AptCharacterSprite  (sizeof = 12) ----
struct AptCharacterSprite {
    /* +0x00 */ AptMovie movie;
};
// static_assert(sizeof(AptCharacterSprite) == 12);  // 32-bit console layout

// ---- AptNativeHash  (sizeof = 20) ----
class AptNativeHash {
    /* +0x00 */ int mnTotalSize;
    /* +0x04 */ AptHashItem* mpData;
    /* +0x08 */ AptValue* mp__proto__;
    /* +0x0c */ AptValue* mpPrototype;
    /* +0x10 */ unsigned int nEventHandlers;
    // --- methods (address @ B4Extern) ---
    // 0x825210: AptValue* __cdecl AptNativeHash::Get__Proto__()
    // 0x824308: void __cdecl AptNativeHash::Set__Proto__(const AptValue* pValue)
    // 0x824378: void __cdecl AptNativeHash::Unset__Proto__()
    // 0x824A50: AptValue* __cdecl AptNativeHash::GetPrototype()
    // 0x8243C8: void __cdecl AptNativeHash::SetPrototype(const AptValue* pValue)
    // 0x824438: void __cdecl AptNativeHash::UnsetPrototype()
    // 0x824488: bool __cdecl AptNativeHash::IsEmpty()
    // 0x8244A0: void __cdecl AptNativeHash::SetEventHandler(int nFlag)
    // 0x8244B0: void __cdecl AptNativeHash::RemoveEventHandler(int nFlag)
    // 0x8244C0: int __cdecl AptNativeHash::HasEventHandler(int nFlag)
    // 0x8244D0: AptValue* __cdecl AptNativeHash::GetAt(const int nIndex)
    // 0x8251B0: virtual AptValue* __cdecl AptNativeHash::GetAt(const AptHashItem* pItem) = 0
    // 0x8244E8: void __cdecl AptNativeHash::SetAt(const int nIndex, const AptValue* pValue)
    // 0x824550: virtual void __cdecl AptNativeHash::SetAt(const AptHashItem* pItem, const AptValue* pValue) = 0
    // 0x8245A8: void __cdecl AptNativeHash::OverwriteAt(const int nIndex, AptValue* pValue)
    // 0x8245F0: virtual void __cdecl AptNativeHash::OverwriteAt(const AptHashItem* pHashItem, AptValue* pValue) = 0
    // 0x824640: virtual void __cdecl AptNativeHash::UnsetAt(const AptHashItem* pHashItem) = 0
    // 0x8550B0: void __cdecl AptNativeHash::AptNativeHash(const int nTotalSize)
    // 0x855100: void __cdecl AptNativeHash::~AptNativeHash()
    // 0x8551E0: void __cdecl AptNativeHash::DestroyGCPointers()
    // 0x8552B0: void __cdecl AptNativeHash::ClearData()
    // 0x8553F0: void __cdecl AptNativeHash::ClearDataNoDelete()
    // 0x855518: AptHashItem* __cdecl AptNativeHash::GetFirstItem()
    // 0x8555A8: AptHashItem* __cdecl AptNativeHash::GetNextItem(AptHashItem* pItem)
    // 0x855630: void __cdecl AptNativeHash::Expand()
    // 0x855788: void __cdecl AptNativeHash::HashSet(const EAStringC* pKey, const AptValue* pValue)
    // 0x855C98: AptHashItem* __cdecl AptNativeHash::HashFindKey(EAStringC* pKey)
    // 0x855F60: void __cdecl AptNativeHash::UpdateObjectMethods(AptValue* pContext, EAStringC* pVar, int bRemove)
    // 0x856050: void __cdecl AptNativeHash::RegisterReferences(AptValue* pFromRef)
    // 0x8561A8: void __cdecl AptNativeHash::Unset(const EAStringC* pKey)
    // 0x8563A0: AptValue* __cdecl AptNativeHash::Lookup(const EAStringC* pKey)
    // 0x8564E8: void __cdecl AptNativeHash::Set(const EAStringC* pKey, const AptValue* pValue)
    // 0x8566F0: void __cdecl AptNativeHash::SetIfNotExists(const EAStringC* pKey, const AptValue* pValue)
    // 0x856730: void __cdecl AptNativeHash::FirstAllocation()
};
// static_assert(sizeof(AptNativeHash) == 20);  // 32-bit console layout

// ---- AptActionQueueC  (sizeof = 20) ----
class AptActionQueueC {
    /* +0x00 */ AptActionQueueC::AptActionPool* m_aActionPool;
    /* +0x04 */ AptActionQueueC::AptActionPool* m_pStartDeque;
    /* +0x08 */ AptActionQueueC::AptActionPool* m_pEndDeque;
    /* +0x0c */ AptActionQueueC::AptActionPool* m_pCurDeque;
    /* +0x10 */ int m_iActionPoolSize;
    // --- methods (address @ B4Extern) ---
    // 0x8251B0: AptActionQueueC::AptActionPool* __cdecl AptActionQueueC::GetFirstItem()
    // 0x824A30: bool __cdecl AptActionQueueC::IsLastItem(AptActionQueueC::AptActionPool* pItem)
    // 0x825210: AptActionQueueC::AptActionPool* __cdecl AptActionQueueC::GetLastItem()
    // 0x824A50: AptActionQueueC::AptActionPool* __cdecl AptActionQueueC::GetCurItem()
    // 0x824A58: void __cdecl AptActionQueueC::SetCurItem(AptActionQueueC::AptActionPool* pItem)
    // 0x828C00: AptActionQueueC::AptActionPool* __cdecl AptActionQueueC::IncrementDequeLocation(AptActionQueueC::AptActionPool* curr)
    // 0x824A60: AptActionQueueC::AptActionPool* __cdecl AptActionQueueC::DecrementDequeLocation(AptActionQueueC::AptActionPool* curr)
    // 0x828C00: AptActionQueueC::AptActionPool* __cdecl AptActionQueueC::GetNextItem(AptActionQueueC::AptActionPool* pItem)
    // 0x85ED60: void __cdecl AptActionQueueC::AddActionBack(AptActionBlock* pActionBlock, AptCIH* pCIH, unsigned int input)
    // 0x85EE00: void __cdecl AptActionQueueC::AddActionFront(AptActionBlock* pActionBlock, AptCIH* pCIH, unsigned int input)
    // 0x85EEB8: void __cdecl AptActionQueueC::AddFunctionBack(AptCIH* pContext, AptValue* pFuncDef, int nParams, unsigned int input)
    // 0x85EF70: void __cdecl AptActionQueueC::AddFunctionFront(AptCIH* pContext, AptValue* pFuncDef, int nParams, unsigned int input)
    // 0x85F028: int __cdecl AptActionQueueC::GetDequeSize()
    // 0x85F068: AptActionQueueC::AptActionPool* __cdecl AptActionQueueC::GetDequeLocation(const int iIndex)
    // 0x85F0E8: void __cdecl AptActionQueueC::RegisterReferences()
    // 0x85FF38: void __cdecl AptActionQueueC::ClearActions()
    // 0x860008: void __cdecl AptActionQueueC::RemoveActionFor(AptCIH* pCIH)
    // 0x861520: void __cdecl AptActionQueueC::AptActionQueueC(unsigned int nSize)
};
// static_assert(sizeof(AptActionQueueC) == 20);  // 32-bit console layout

// ---- AptActionQueueC::AptActionPool  (sizeof = 20) ----
struct AptActionQueueC::AptActionPool {
    /* +0x00 */ AptActionQueueC::APT_ACTION_TYPE eActionType;
    /* +0x04 */ unsigned int input;
    /* +0x08 */ AptActionQueueC::AptAction action;
    /* +0x08 */ AptActionQueueC::AptFunction function;
};
// static_assert(sizeof(AptActionQueueC::AptActionPool) == 20);  // 32-bit console layout

// ---- AptActionQueueC::AptFunction  (sizeof = 12) ----
struct AptActionQueueC::AptFunction {
    /* +0x00 */ AptCIH* pContext;
    /* +0x04 */ AptValue* pFuncDef;
    /* +0x08 */ int nParams;
};
// static_assert(sizeof(AptActionQueueC::AptFunction) == 12);  // 32-bit console layout

// ---- AptActionQueueC::AptAction  (sizeof = 12) ----
struct AptActionQueueC::AptAction {
    /* +0x00 */ int nFrame;
    /* +0x04 */ AptActionBlock* pBlock;
    /* +0x08 */ AptCIH* pCIH;
};
// static_assert(sizeof(AptActionQueueC::AptAction) == 12);  // 32-bit console layout

// ---- AptMovieClip  (sizeof = 32) ----
class AptMovieClip : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x828BB8: virtual void __cdecl AptMovieClip::~AptMovieClip()
    // 0x84EE20: void __cdecl AptMovieClip::AptMovieClip()
};
// static_assert(sizeof(AptMovieClip) == 32);  // 32-bit console layout

// ---- AptScriptFunction1  (sizeof = 52) ----
class AptScriptFunction1 : public AptScriptFunctionBase {
    /* +0x30 */ AptAction_DefineFunction* mpFunction;
    // --- methods (address @ B4Extern) ---
    // 0x85DF80: virtual void __cdecl AptScriptFunction1::~AptScriptFunction1()
    // 0x85E3F8: void __cdecl AptScriptFunction1::AptScriptFunction1(AptScriptFunctionBase* pCreatorFunction, AptAction_DefineFunction* _pFunction, AptCIH* pCurCIH)
    // 0x85E450: void __cdecl AptScriptFunction1::AptScriptFunction1(AptScriptFunction1* pOrigFunc, AptCIH* pCurCIH)
    // 0x85E658: virtual const char* __cdecl AptScriptFunction1::GetName()
    // 0x85E668: virtual unsigned int __cdecl AptScriptFunction1::GetNumArguments()
    // 0x85E678: virtual const unsigned char* __cdecl AptScriptFunction1::GetByteCodeBase()
    // 0x85E688: virtual unsigned int __cdecl AptScriptFunction1::GetByteCodeSize()
    // 0x85E698: virtual AptConstantPool __cdecl AptScriptFunction1::GetConstantPool()
    // 0x85E6B8: virtual void __cdecl AptScriptFunction1::SetArgument(AptValue* pValue, int nIndex)
    // 0x85E958: virtual AptScriptFunctionBase* __cdecl AptScriptFunction1::Duplicate(AptCIH* pCurCIH)
};
// static_assert(sizeof(AptScriptFunction1) == 52);  // 32-bit console layout

// ---- AptSharedPtr<AptFile>  (sizeof = 4) ----
class AptSharedPtr<AptFile> {
    /* +0x00 */ AptFile* pData;
};
// static_assert(sizeof(AptSharedPtr<AptFile>) == 4);  // 32-bit console layout

// ---- AptValue::<unnamed-tag>::<unnamed-tag>  (sizeof = 4) ----
struct AptValue::<unnamed-tag>::<unnamed-tag> {
    /* +0x00 */ unsigned int mbIsAllocated : 1;
    /* +0x00 */ unsigned int mbHasRegisterReferenceMark : 1;
    /* +0x00 */ unsigned int mbIsInDeferredVector : 1;
    /* +0x00 */ unsigned int mbDestroyedGC : 1;
    /* +0x00 */ unsigned int mbIsDefined : 1;
    /* +0x00 */ unsigned int mbAllowsDelayedDeletion : 1;
    /* +0x00 */ unsigned int mnReferenceCount : 12;
    /* +0x00 */ unsigned int mnGCRootCount : 6;
    /* +0x00 */ unsigned int mnMaxRefCountHit : 1;
    /* +0x00 */ AptVirtualFunctionTable_Indices meValueType : 7;
};
// static_assert(sizeof(AptValue::<unnamed-tag>::<unnamed-tag>) == 4);  // 32-bit console layout

// ---- AptValue  (sizeof = 8) ----
class AptValue {
    /* +0x00 */ void* __vftable;
    /* +0x04 */ struct {
        unsigned int mbIsAllocated : 1;
        unsigned int mbHasRegisterReferenceMark : 1;
        unsigned int mbIsInDeferredVector : 1;
        unsigned int mbDestroyedGC : 1;
        unsigned int mbIsDefined : 1;
        unsigned int mbAllowsDelayedDeletion : 1;
        unsigned int mnReferenceCount : 12;
        unsigned int mnGCRootCount : 6;
        unsigned int mnMaxRefCountHit : 1;
        AptVirtualFunctionTable_Indices meValueType : 7;
    };
    /* +0x04 */ unsigned int mnValueData;
    // --- methods (address @ B4Extern) ---
    // 0x824B70: bool __cdecl AptValue::GetMaxRefCountHit()
    // 0x824B80: unsigned int __cdecl AptValue::getRefCount()
    // 0x824B90: bool __cdecl AptValue::getGCMark()
    // 0x824BB0: unsigned int __cdecl AptValue::getGCRoot()
    // 0x824BC0: void __cdecl AptValue::incGCRoot()
    // 0x824BE8: void __cdecl AptValue::decGCRoot()
    // 0x824C10: bool __cdecl AptValue::IsReleaseAtEnd()
    // 0x7C9D90: AptLookup* __cdecl AptValue::c_lookup()
    // 0x7C9D90: AptInteger* __cdecl AptValue::c_integer()
    // 0x7C9D90: AptRegister* __cdecl AptValue::c_register()
    // 0x7C9D90: AptFloat* __cdecl AptValue::c_float()
    // 0x824C30: AptString* __cdecl AptValue::c_string()
    // 0x7C9D90: AptBoolean* __cdecl AptValue::c_boolean()
    // 0x7C9D90: AptScriptFunctionBase* __cdecl AptValue::c_scriptfunction()
    // 0x7C9D90: AptNativeFunction* __cdecl AptValue::c_nativefunction()
    // 0x7C9D90: AptCIH* __cdecl AptValue::c_cih(bool bUndefOK)
    // 0x7C9D90: AptArray* __cdecl AptValue::c_array()
    // 0x7C9D90: AptKey* __cdecl AptValue::c_key()
    // 0x7C9D90: AptGlobal* __cdecl AptValue::c_global()
    // 0x7C9D90: AptMathObj* __cdecl AptValue::c_math()
    // 0x7C9D90: AptScriptColour* __cdecl AptValue::c_scriptcolour()
    // 0x7C9D90: AptObject* __cdecl AptValue::c_object()
    // 0x7C9D90: AptPrototype* __cdecl AptValue::c_prototype()
    // 0x7C9D90: AptDate* __cdecl AptValue::c_date()
    // 0x7C9D90: AptTextFormat* __cdecl AptValue::c_textformat()
    // 0x7C9D90: AptMovieClip* __cdecl AptValue::c_movieClip()
    // 0x7C9D90: AptXmlNode* __cdecl AptValue::c_xmlnode()
    // 0x7C9D90: AptXml* __cdecl AptValue::c_xml()
    // 0x7C9D90: AptXmlAttributes* __cdecl AptValue::c_xmlattributes()
    // 0x7C9D90: AptLoadVars* __cdecl AptValue::c_loadvars()
    // 0x7C9D90: AptStage* __cdecl AptValue::c_stage()
    // 0x824C48: bool __cdecl AptValue::isXmlNode()
    // 0x824C68: bool __cdecl AptValue::isXml()
    // 0x824C88: bool __cdecl AptValue::isXmlAttributes()
    // 0x824CA8: bool __cdecl AptValue::isLoadVars()
    // 0x824CC8: bool __cdecl AptValue::isNone()
    // 0x824CE8: bool __cdecl AptValue::isLookup()
    // 0x824D30: bool __cdecl AptValue::isRegister()
    // 0x824D78: bool __cdecl AptValue::isNativeFunction()
    // 0x824DC0: bool __cdecl AptValue::isScriptFunction()
    // 0x824E10: bool __cdecl AptValue::isExtern()
    // 0x824E58: bool __cdecl AptValue::isFrameStack()
    // 0x824EA0: bool __cdecl AptValue::isArray()
    // 0x824EE8: bool __cdecl AptValue::isKey()
    // 0x824F30: bool __cdecl AptValue::isMath()
    // 0x824F78: bool __cdecl AptValue::isScriptColour()
    // 0x824FC0: bool __cdecl AptValue::isCIH(bool bUndefOK)
    // 0x825028: bool __cdecl AptValue::isPrototype()
    // 0x825070: bool __cdecl AptValue::isDate()
    // 0x8250B8: bool __cdecl AptValue::isTextFormat()
    // 0x825100: bool __cdecl AptValue::isMovieClip()
    // 0x825148: bool __cdecl AptValue::isStage()
    // 0x828C50: void __cdecl AptValue::AptValue(AptVirtualFunctionTable_Indices eType, AptValue::CIH_ONLY eCIH)
    // 0x82BC88: int __cdecl AptValue::toInteger()
    // 0x82BE78: float __cdecl AptValue::toFloat()
    // 0x82C050: bool __cdecl AptValue::toBool()
    // 0x82C288: void __cdecl AptValue::toString(EAStringC& sBuf)
    // 0x82D130: EAStringC __cdecl AptValue::urlEncode()
    // 0x82D3E8: EAStringC __cdecl AptValue::urlEncodeCustomRender()
    // 0x82D710: int __cdecl AptValue::isMCInParentChain()
    // 0x82D7E8: bool __cdecl AptValue::CanCreateScriptObject()
    // 0x82D8D8: virtual void __cdecl AptValue::AddRef()
    // 0x82D908: virtual void __cdecl AptValue::Release()
    // 0x82DAD8: void __cdecl AptValue::toString(char* szBuf)
    // 0x82F2A0: AptValue* __cdecl AptValue::findChild(EAStringC* pName, AptValue* pWith)
};
// static_assert(sizeof(AptValue) == 8);  // 32-bit console layout

// ---- AptScriptFunctionBase  (sizeof = 48) ----
class AptScriptFunctionBase : public AptObject {
    /* +0x20 */ AptCIH* mpCIH;
    /* +0x24 */ AptCIH* mpParentAnim;
    /* +0x28 */ AptFrameStack* mpCreatorScope;
    /* +0x2c */ unsigned short mnFrameStackReserve;
    // --- methods (address @ B4Extern) ---
    // 0x85D7B8: virtual void __cdecl AptScriptFunctionBase::InitializeStaticData(AptInitParmsT& pInitParams) = 0
    // 0x85D860: virtual void __cdecl AptScriptFunctionBase::ShutdownStaticData() = 0
    // 0x85D8A0: virtual void* __cdecl AptScriptFunctionBase::PushStaticData() = 0
    // 0x85D8D0: virtual void __cdecl AptScriptFunctionBase::PopStaticData(void* pPushValue) = 0
    // 0x85D950: virtual void __cdecl AptScriptFunctionBase::PreDestroy()
    // 0x85D958: virtual void __cdecl AptScriptFunctionBase::RegisterReferences()
    // 0x85DA78: virtual void __cdecl AptScriptFunctionBase::DestroyGCPointers()
    // 0x85DB10: virtual void __cdecl AptScriptFunctionBase::SetupBeforeExecution(_AptScriptFunctionState* pState, AptValue* pContext)
    // 0x85DB28: virtual void __cdecl AptScriptFunctionBase::CleanupAfterExecution(_AptScriptFunctionState* pState)
    // 0x85DB88: virtual AptValue* __cdecl AptScriptFunctionBase::GetRegisterValue(int nIndex) = 0
    // 0x85DBA0: virtual void __cdecl AptScriptFunctionBase::SetRegisterValue(int nIndex, AptValue* pNewValue) = 0
    // 0x85DF38: virtual void __cdecl AptScriptFunctionBase::~AptScriptFunctionBase()
    // 0x85E010: void __cdecl AptScriptFunctionBase::AptScriptFunctionBase(AptVirtualFunctionTable_Indices eType, AptScriptFunctionBase* pCreatorFunction, AptCIH* pCurCIH, bool bNeedsPrototype)
    // 0x85E240: void __cdecl AptScriptFunctionBase::AptScriptFunctionBase(AptVirtualFunctionTable_Indices eType, AptScriptFunctionBase* pOrigFunc, AptCIH* pCurCIH)
    // 0x85E5C8: virtual void __cdecl AptScriptFunctionBase::CreatingNestedFunction()
    // 0x8248E0: bool __cdecl AptScriptFunctionBase::ExistsInLocalScope(EAStringC* pVarName)
    // 0x824948: bool __cdecl AptScriptFunctionBase::SetWhereExistsInScopeChain(EAStringC* pVarName, AptValue* pValue)
    // 0x824978: AptValue* __cdecl AptScriptFunctionBase::GetInScopeChain(EAStringC* pVarName)
    // 0x8297D0: void __cdecl AptScriptFunctionBase::CreateFrameStack()
    // 0x82A060: void __cdecl AptScriptFunctionBase::SetInLocalScope(EAStringC* pVarName, AptValue* pValue)
};
// static_assert(sizeof(AptScriptFunctionBase) == 48);  // 32-bit console layout

// ---- AptLinkerThingy  (sizeof = 16) ----
struct AptLinkerThingy : public AptSharedPtrRefCount {
    /* +0x04 */ AptSharedPtr<AptFile> mFile;
    /* +0x08 */ AptCIH* pTarget;
    /* +0x0c */ bool mAttachedToMovie;
    // --- methods (address @ B4Extern) ---
    // 0x854740: void __cdecl AptLinkerThingy::AptLinkerThingy(AptSharedPtr<AptFile>* file, AptCIH* target)
};
// static_assert(sizeof(AptLinkerThingy) == 16);  // 32-bit console layout

// ---- AptSharedPtr<AptLinkerThingy>  (sizeof = 4) ----
class AptSharedPtr<AptLinkerThingy> {
    /* +0x00 */ AptLinkerThingy* pData;
};
// static_assert(sizeof(AptSharedPtr<AptLinkerThingy>) == 4);  // 32-bit console layout

// ---- AptFloat  (sizeof = 12) ----
class AptFloat : public AptValueNoGC {
    /* +0x08 */ float mfValue;
    /* +0x08 */ AptFloat* mpNextFree;
    // --- methods (address @ B4Extern) ---
    // 0x85CFD8: virtual void __cdecl AptFloat::ClearPool() = 0
    // 0x85D058: virtual void __cdecl AptFloat::DeleteThis()
    // 0x85D070: virtual void __cdecl AptFloat::ForceDelete()
    // 0x825218: void __cdecl AptFloat::Destroy()
    // 0x825230: float __cdecl AptFloat::GetFloat()
};
// static_assert(sizeof(AptFloat) == 12);  // 32-bit console layout

// ---- AptnCXForm  (sizeof = 8) ----
struct AptnCXForm {
    /* +0x00 */ unsigned int nScale;
    /* +0x04 */ unsigned int nBias;
};
// static_assert(sizeof(AptnCXForm) == 8);  // 32-bit console layout

// ---- AptActionSetup  (sizeof = 1) ----
struct AptActionSetup {
    /* +0x00 */ AptRect rBounds;
    /* +0x10 */ void* zID;
};
// static_assert(sizeof(AptActionSetup) == 1);  // 32-bit console layout

// ---- AptCharacterButtonInst  (sizeof = 24) ----
struct AptCharacterButtonInst : public AptCharacterInst {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptCharacterButtonInst) == 24);  // 32-bit console layout

// ---- AptExtObject  (sizeof = 16) ----
class AptExtObject : public AptValueGC {
    /* +0x08 */ AptNativeHash* mpNativeHash;
    /* +0x0c */ unsigned int mnObjectSize;
    // --- methods (address @ B4Extern) ---
    // 0x82B3C0: void __cdecl AptExtObject::SetFunction(const char* pKey, AptNativeFunction* pFunction)
    // 0x82B440: virtual AptValue* __cdecl AptExtObject::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x82B450: virtual bool __cdecl AptExtObject::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue)
    // 0x82B480: virtual AptNativeHash* __cdecl AptExtObject::GetNativeHashVirtual()
    // 0x82B488: virtual bool __cdecl AptExtObject::ContainsNativeHashVirtual()
    // 0x82B490: virtual void __cdecl AptExtObject::RegisterReferences()
    // 0x82B4A0: virtual void __cdecl AptExtObject::DestroyGCPointers()
    // 0x82B4A8: AptValue* __cdecl AptExtObject::Lookup(const EAStringC* pKey)
    // 0x82B4B0: void __cdecl AptExtObject::Set(const EAStringC* pKey, const AptValue* pValue)
    // 0x82B4B8: virtual void __cdecl AptExtObject::~AptExtObject()
    // 0x82B528: void __cdecl AptExtObject::AptExtObject(const int iNumMembers)
    // 0x825F68: virtual AptValue* __cdecl AptExtObject::GetUndefinedValue() = 0
};
// static_assert(sizeof(AptExtObject) == 16);  // 32-bit console layout

// ---- AptGlobal  (sizeof = 32) ----
class AptGlobal : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x87D7A0: virtual AptValue* __cdecl AptGlobal::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x87D828: virtual bool __cdecl AptGlobal::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue)
    // 0x825238: void __cdecl AptGlobal::Set(const EAStringC* pKey, const AptValue* pValue)
    // 0x825240: AptValue* __cdecl AptGlobal::Lookup(const EAStringC* pKey)
    // 0x828BB8: virtual void __cdecl AptGlobal::~AptGlobal()
    // 0x830180: void __cdecl AptGlobal::AptGlobal()
};
// static_assert(sizeof(AptGlobal) == 32);  // 32-bit console layout

// ---- AptGlobalExtensionObject  (sizeof = 32) ----
class AptGlobalExtensionObject : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x825238: void __cdecl AptGlobalExtensionObject::Set(const EAStringC* pKey, const AptValue* pValue)
    // 0x825240: AptValue* __cdecl AptGlobalExtensionObject::Lookup(const EAStringC* pKey)
    // 0x828BB8: virtual void __cdecl AptGlobalExtensionObject::~AptGlobalExtensionObject()
    // 0x830268: void __cdecl AptGlobalExtensionObject::AptGlobalExtensionObject()
};
// static_assert(sizeof(AptGlobalExtensionObject) == 32);  // 32-bit console layout

// ---- AptControlPlaceObject2  (sizeof = 60) ----
struct AptControlPlaceObject2 {
    /* +0x00 */ AptPlaceObjectFlags eFlags;
    /* +0x04 */ int nDepth;
    /* +0x08 */ int nCharacterID;
    /* +0x0c */ AptMatrix matrix;
    /* +0x24 */ AptnCXForm ncxform;
    /* +0x2c */ float fRatio;
    /* +0x30 */ char* szName;
    /* +0x34 */ int nClipDepth;
    /* +0x38 */ AptEventActionSet* pActions;
};
// static_assert(sizeof(AptControlPlaceObject2) == 60);  // 32-bit console layout

// ---- AptAnalogStickInfo  (sizeof = 16) ----
struct AptAnalogStickInfo {
    /* +0x00 */ float fXAxisValue;
    /* +0x04 */ float fYAxisValue;
    /* +0x08 */ unsigned char nController;
    /* +0x0c */ AptInputType nSide;
};
// static_assert(sizeof(AptAnalogStickInfo) == 16);  // 32-bit console layout

// ---- AptSingleListPolicy  (sizeof = 1) ----
struct AptSingleListPolicy {
    /* +0x00 */ int nEventActions;
    /* +0x04 */ AptEventActionBlock* aEventActions;
};
// static_assert(sizeof(AptSingleListPolicy) == 1);  // 32-bit console layout

// ---- AptScriptColour  (sizeof = 36) ----
class AptScriptColour : public AptObject {
    /* +0x20 */ AptCIH* pSprite;
    // --- methods (address @ B4Extern) ---
    // 0x873FE8: virtual void __cdecl AptScriptColour::CleanNativeFunctions() = 0
    // 0x8740B0: virtual void __cdecl AptScriptColour::RegisterReferences()
    // 0x874130: virtual void __cdecl AptScriptColour::DestroyGCPointers()
    // 0x874188: virtual void __cdecl AptScriptColour::~AptScriptColour()
    // 0x8741D0: virtual AptValue* __cdecl AptScriptColour::sMethod_setRGB(AptValue* pThis, int nParams) = 0
    // 0x8742C8: virtual AptValue* __cdecl AptScriptColour::sMethod_setTransform(AptValue* pThis, int nParams) = 0
    // 0x874550: void __cdecl AptScriptColour::AptScriptColour(const AptValue* pMovie)
    // 0x8746F0: virtual AptValue* __cdecl AptScriptColour::sMethod_getRGB(AptValue* pThis, int nParams) = 0
    // 0x8748C0: virtual AptValue* __cdecl AptScriptColour::sMethod_getTransform(AptValue* pThis, int nParams) = 0
    // 0x8752E0: virtual AptValue* __cdecl AptScriptColour::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
};
// static_assert(sizeof(AptScriptColour) == 36);  // 32-bit console layout

// ---- AptValuePtrStack<AptValue>  (sizeof = 12) ----
class AptValuePtrStack<AptValue> {
    /* +0x00 */ int m_nElements;
    /* +0x04 */ int m_nSize;
    /* +0x08 */ AptValue** m_aElements;
};
// static_assert(sizeof(AptValuePtrStack<AptValue>) == 12);  // 32-bit console layout

// ---- AptPseudoData_t  (sizeof = 28) ----
struct AptPseudoData_t {
    /* +0x00 */ AptCharacter* pCharacter;
    /* +0x04 */ AptMatrix* matrix;
    /* +0x08 */ AptnCXForm* ncxform;
    /* +0x0c */ AptEventActionSet* pActions;
    /* +0x10 */ float fRatio;
    /* +0x14 */ int eFlags;
    /* +0x18 */ int nFrameCreated : 16;
    /* +0x18 */ int nClipDepth : 16;
    // --- methods (address @ B4Extern) ---
    // 0x8755E0: void __cdecl AptPseudoData_t::AptPseudoData_t(AptControl* pControl, int nFrame, AptCharacter* pNewCharacter)
};
// static_assert(sizeof(AptPseudoData_t) == 28);  // 32-bit console layout

// ---- AptSharedPtrRefCount  (sizeof = 4) ----
struct AptSharedPtrRefCount {
    /* +0x00 */ int mRefCount;
};
// static_assert(sizeof(AptSharedPtrRefCount) == 4);  // 32-bit console layout

// ---- AptXmlNode  (sizeof = 32) ----
class AptXmlNode : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x873F80: virtual void __cdecl AptXmlNode::CleanNativeFunctions() = 0
    // 0x873F88: virtual void __cdecl AptXmlNode::~AptXmlNode()
    // 0x84EEF8: void __cdecl AptXmlNode::AptXmlNode(AptVirtualFunctionTable_Indices eType, IAptXmlNode* pIXmlNodeParam)
};
// static_assert(sizeof(AptXmlNode) == 32);  // 32-bit console layout

// ---- AptString  (sizeof = 16) ----
class AptString : public AptValueNoGC {
    /* +0x08 */ EAStringC str;
    /* +0x0c */ AptString* mpNext;
    // --- methods (address @ B4Extern) ---
    // 0x828E30: void __cdecl AptString::Destroy()
    // 0x8309D8: virtual void __cdecl AptString::CleanNativeFunctions() = 0
    // 0x830BE0: virtual AptValue* __cdecl AptString::sMethod_lastIndexOf(AptValue* pThis, int nParams) = 0
    // 0x830BF0: void __cdecl AptString::printf(const char* szFormat, ...)
    // 0x830CD0: virtual void __cdecl AptString::~AptString()
    // 0x830D48: virtual void __cdecl AptString::DeleteThis()
    // 0x830DE8: virtual void __cdecl AptString::ForceDelete()
    // 0x830E88: void __cdecl AptString::AptString()
    // 0x830F30: void __cdecl AptString::AptString(const char* szValue)
    // 0x830FE8: virtual AptValue* __cdecl AptString::sMethod_indexOf(AptValue* pThis, int nParams) = 0
    // 0x831298: virtual AptString* __cdecl AptString::Create(const char* szValue) = 0
    // 0x831398: virtual AptValue* __cdecl AptString::sMethod_charAt(AptValue* pThis, int nParams) = 0
    // 0x831530: virtual AptValue* __cdecl AptString::sMethod_charCodeAt(AptValue* pThis, int nParams) = 0
    // 0x831750: virtual AptValue* __cdecl AptString::sMethod_concat(AptValue* pThis, int nParams) = 0
    // 0x831950: virtual AptValue* __cdecl AptString::sMethod_fromCharCode(AptValue* pThis, int nParams) = 0
    // 0x831B48: virtual AptValue* __cdecl AptString::sMethod_slice(AptValue* pThis, int nParams) = 0
    // 0x831E78: virtual AptValue* __cdecl AptString::sMethod_split(AptValue* pThis, int nParams) = 0
    // 0x832438: virtual AptValue* __cdecl AptString::sMethod_substr(AptValue* pThis, int nParams) = 0
    // 0x8326B8: virtual AptValue* __cdecl AptString::sMethod_substring(AptValue* pThis, int nParams) = 0
    // 0x832960: virtual AptValue* __cdecl AptString::sMethod_toLowerCase(AptValue* pThis, int nParams) = 0
    // 0x832AD8: virtual AptValue* __cdecl AptString::sMethod_toUpperCase(AptValue* pThis, int nParams) = 0
    // 0x832C50: virtual AptValue* __cdecl AptString::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x8333B0: void __cdecl AptString::cpy(EAStringC* pStr)
};
// static_assert(sizeof(AptString) == 16);  // 32-bit console layout

// ---- AptXmlAttributePair  (sizeof = 8) ----
class AptXmlAttributePair {
    /* +0x00 */ char* pKey;
    /* +0x04 */ char* pValue;
};
// static_assert(sizeof(AptXmlAttributePair) == 8);  // 32-bit console layout

// ---- AptCXForm  (sizeof = 32) ----
struct AptCXForm {
    /* +0x00 */ float scale[4];
    /* +0x10 */ float translate[4];
};
// static_assert(sizeof(AptCXForm) == 32);  // 32-bit console layout

// ---- AptCharacterMorphInst  (sizeof = 28) ----
struct AptCharacterMorphInst : public AptCharacterInst {
    /* +0x18 */ float fRatio;
};
// static_assert(sizeof(AptCharacterMorphInst) == 28);  // 32-bit console layout

// ---- AptAction_DefineFunction  (sizeof = 24) ----
struct AptAction_DefineFunction {
    /* +0x00 */ const char* szName;
    /* +0x04 */ int nParams;
    /* +0x08 */ char** aszParams;
    /* +0x0c */ int nCodeSize;
    /* +0x10 */ AptConstantPool constantPool;
};
// static_assert(sizeof(AptAction_DefineFunction) == 24);  // 32-bit console layout

// ---- AptRegisterParam  (sizeof = 8) ----
struct AptRegisterParam {
    /* +0x00 */ unsigned int nRegister;
    /* +0x04 */ char* szParamName;
};
// static_assert(sizeof(AptRegisterParam) == 8);  // 32-bit console layout

// ---- AptCharacterFont  (sizeof = 12) ----
struct AptCharacterFont {
    /* +0x00 */ char* szName;
    /* +0x04 */ int nGlyphs;
    /* +0x08 */ AptCharacter** apGlyphs;
};
// static_assert(sizeof(AptCharacterFont) == 12);  // 32-bit console layout

// ---- AptFileSavedInputState  (sizeof = 8) ----
struct AptFileSavedInputState {
    /* +0x00 */ EAStringC mName;
    /* +0x04 */ AptFileSavedInputState::State mState;
};
// static_assert(sizeof(AptFileSavedInputState) == 8);  // 32-bit console layout

// ---- AptValueGC  (sizeof = 8) ----
class AptValueGC : public AptValue {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptValueGC) == 8);  // 32-bit console layout

// ---- AptPseudoDisplayList  (sizeof = 8) ----
class AptPseudoDisplayList {
    /* +0x00 */ AptPseudoCIH_t* pHead;
    /* +0x04 */ AptCIH* pParentCIH;
    // --- methods (address @ B4Extern) ---
    // 0x8249C0: virtual AptVirtualFunctionTable_Indices __cdecl AptPseudoDisplayList::CharTypeToAptVFT(AptCharacterType eType) = 0
    // 0x824A20: AptPseudoCIH_t* __cdecl AptPseudoDisplayList::GetFirstItem()
    // 0x8251B0: AptCIH* __cdecl AptPseudoDisplayList::GetParentSprite()
    // 0x879010: void __cdecl AptPseudoDisplayList::AptPseudoDisplayList(AptCIH* pParent)
    // 0x87C388: void __cdecl AptPseudoDisplayList::~AptPseudoDisplayList()
    // 0x875740: void __cdecl AptPseudoDisplayList::FindInst(int nDepth, AptPseudoCIH_t** ppPrev, AptPseudoCIH_t** ppItem)
    // 0x875798: void __cdecl AptPseudoDisplayList::Insert(AptPseudoCIH_t* pPrev, AptPseudoCIH_t* pNewItem)
    // 0x875E48: void __cdecl AptPseudoDisplayList::ClearList()
    // 0x875EC8: void __cdecl AptPseudoDisplayList::Remove(AptPseudoCIH_t* pItem)
    // 0x876CA8: void __cdecl AptPseudoDisplayList::Insert(AptPseudoCIH_t* pItem)
    // 0x876DA0: void __cdecl AptPseudoDisplayList::Insert(AptPseudoCIH_t* pNewItem, AptPseudoCIH_t* pPrev, AptPseudoCIH_t* pOldItem)
    // 0x876E30: void __cdecl AptPseudoDisplayList::Remove(int nDepth)
};
// static_assert(sizeof(AptPseudoDisplayList) == 8);  // 32-bit console layout

// ---- AptMathObj  (sizeof = 32) ----
class AptMathObj : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x828BB8: virtual void __cdecl AptMathObj::~AptMathObj()
    // 0x8622A8: virtual void __cdecl AptMathObj::CleanNativeFunctions() = 0
    // 0x862F28: virtual AptValue* __cdecl AptMathObj::sMethod_sin(AptValue* pThis, int nParams) = 0
    // 0x8630E0: virtual AptValue* __cdecl AptMathObj::sMethod_cos(AptValue* pThis, int nParams) = 0
    // 0x863298: virtual AptValue* __cdecl AptMathObj::sMethod_atan2(AptValue* pThis, int nParams) = 0
    // 0x863430: virtual AptValue* __cdecl AptMathObj::sMethod_round(AptValue* pThis, int nParams) = 0
    // 0x863610: virtual AptValue* __cdecl AptMathObj::sMethod_min(AptValue* pThis, int nParams) = 0
    // 0x8637C0: virtual AptValue* __cdecl AptMathObj::sMethod_max(AptValue* pThis, int nParams) = 0
    // 0x863970: virtual AptValue* __cdecl AptMathObj::sMethod_abs(AptValue* pThis, int nParams) = 0
    // 0x863C58: virtual AptValue* __cdecl AptMathObj::sMethod_acos(AptValue* pThis, int nParams) = 0
    // 0x863E10: virtual AptValue* __cdecl AptMathObj::sMethod_asin(AptValue* pThis, int nParams) = 0
    // 0x863FC8: virtual AptValue* __cdecl AptMathObj::sMethod_atan(AptValue* pThis, int nParams) = 0
    // 0x864180: virtual AptValue* __cdecl AptMathObj::sMethod_ceil(AptValue* pThis, int nParams) = 0
    // 0x864338: virtual AptValue* __cdecl AptMathObj::sMethod_exp(AptValue* pThis, int nParams) = 0
    // 0x8644F0: virtual AptValue* __cdecl AptMathObj::sMethod_floor(AptValue* pThis, int nParams) = 0
    // 0x8646A8: virtual AptValue* __cdecl AptMathObj::sMethod_log(AptValue* pThis, int nParams) = 0
    // 0x864860: virtual AptValue* __cdecl AptMathObj::sMethod_pow(AptValue* pThis, int nParams) = 0
    // 0x8649F8: virtual AptValue* __cdecl AptMathObj::sMethod_random(AptValue* pThis, int nParams) = 0
    // 0x864B80: virtual AptValue* __cdecl AptMathObj::sMethod_sqrt(AptValue* pThis, int nParams) = 0
    // 0x864D38: virtual AptValue* __cdecl AptMathObj::sMethod_tan(AptValue* pThis, int nParams) = 0
    // 0x867F78: virtual AptValue* __cdecl AptMathObj::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x82FFB0: void __cdecl AptMathObj::AptMathObj()
};
// static_assert(sizeof(AptMathObj) == 32);  // 32-bit console layout

// ---- AptMemoryAllocationsT  (sizeof = 32) ----
struct AptMemoryAllocationsT {
    /* +0x00 */ unsigned int nAptUpdateAllocations;
    /* +0x04 */ unsigned int nAptUpdateDeletions;
    /* +0x08 */ unsigned int nAptUpdateAllocationSize;
    /* +0x0c */ unsigned int nAptUpdateDeletionSize;
    /* +0x10 */ unsigned int nAptUpdateAllocationsGC;
    /* +0x14 */ unsigned int nAptUpdateDeletionsGC;
    /* +0x18 */ unsigned int nAptUpdateAllocationGCSize;
    /* +0x1c */ unsigned int nAptUpdateDeletionGCSize;
    // --- methods (address @ B4Extern) ---
    // 0x826118: void __cdecl AptMemoryAllocationsT::Reset()
};
// static_assert(sizeof(AptMemoryAllocationsT) == 32);  // 32-bit console layout

// ---- AptTextFormat  (sizeof = 64) ----
class AptTextFormat {
    // --- methods (address @ B4Extern) ---
    // 0x8299D8: virtual void __cdecl AptTextFormat::~AptTextFormat()
    // 0x84EB38: void __cdecl AptTextFormat::AptTextFormat(AptValue* pFName, float fFonstSize, unsigned int nFontColor, int isBold, int isItalic, int isUnderline, int nUrl, int nTarget, AptValue* pStringAlignment, int nLMargin, int nRMargin, int nIndentation, int nLeading)
    // 0x873DE0: void __cdecl AptTextFormat::AptTextFormat(TextFormat* pNewTextObj)
    // 0x87C930: virtual bool __cdecl AptTextFormat::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue)
    // 0x87CFE8: virtual AptValue* __cdecl AptTextFormat::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
};
// static_assert(sizeof(AptTextFormat) == 64);  // 32-bit console layout

// ---- AptCharacterSpriteInst  (sizeof = 48) ----
struct AptCharacterSpriteInst : public AptCharacterSpriteInstBase {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptCharacterSpriteInst) == 48);  // 32-bit console layout

// ---- AptCharacterStaticText  (sizeof = 48) ----
struct AptCharacterStaticText {
    /* +0x00 */ AptRect rBounds;
    /* +0x10 */ AptMatrix matrix;
    /* +0x28 */ int nFontRecords;
    /* +0x2c */ AptCharacterStaticTextRecords* aRecords;
};
// static_assert(sizeof(AptCharacterStaticText) == 48);  // 32-bit console layout

// ---- AptConstFile  (sizeof = 32) ----
struct AptConstFile {
    /* +0x00 */ char aMagic[20];
    /* +0x14 */ AptCharacter* pMainCharacter;
    /* +0x18 */ int nConstants;
    /* +0x1c */ AptConstantTable* aConstants;
};
// static_assert(sizeof(AptConstFile) == 32);  // 32-bit console layout

// ---- AptExtern  (sizeof = 8) ----
class AptExtern : public AptValueNoGC {
    // --- methods (address @ B4Extern) ---
    // 0x5A93C8: virtual void __cdecl AptExtern::~AptExtern()
    // 0x82FE78: void __cdecl AptExtern::AptExtern()
    // 0x7C9D90: virtual void __cdecl AptExtern::AddRef()
    // 0x7C9D90: virtual void __cdecl AptExtern::Release()
    // 0x82FF00: virtual bool __cdecl AptExtern::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue)
};
// static_assert(sizeof(AptExtern) == 8);  // 32-bit console layout

// ---- AptCharacter  (sizeof = 60) ----
struct AptCharacter {
    /* +0x00 */ AptCharacterType eType;
    /* +0x04 */ AptCharacter* pParentAnim;
    /* +0x08 */ AptCharacterShape shape;
    /* +0x08 */ AptCharacterMorph morph;
    /* +0x08 */ AptCharacterText text;
    /* +0x08 */ AptCharacterFont font;
    /* +0x08 */ AptCharacterSprite sprite;
    /* +0x08 */ AptCharacterBitmap bitmap;
    /* +0x08 */ AptCharacterAnimation animation;
    /* +0x08 */ AptCharacterStaticText statictext;
    // --- methods (address @ B4Extern) ---
    // 0x86B3B0: void __cdecl AptCharacter::render(AptRenderingContext* pRenderingContext, AptMaskRenderOperation eMaskOperation, AptMatrix* pMatrix)
    // 0x86B428: void __cdecl AptCharacter::_getBoundingRect(AptRenderingContext* pRenderingContext, AptRect* pRect, AptMatrix* pMatrix)
};
// static_assert(sizeof(AptCharacter) == 60);  // 32-bit console layout

// ---- AptBoolean  (sizeof = 12) ----
class AptBoolean : public AptValueNoGC {
    /* +0x08 */ bool mbValue;
    /* +0x08 */ AptBoolean* mpNextFree;
    // --- methods (address @ B4Extern) ---
    // 0x85CE78: virtual void __cdecl AptBoolean::ClearPool() = 0
    // 0x85CEF8: virtual void __cdecl AptBoolean::DeleteThis()
    // 0x85CF10: virtual void __cdecl AptBoolean::ForceDelete()
    // 0x8251D8: void __cdecl AptBoolean::Destroy()
    // 0x8251F0: bool __cdecl AptBoolean::GetBool()
};
// static_assert(sizeof(AptBoolean) == 12);  // 32-bit console layout

// ---- AptAllocateStringParameters  (sizeof = 112) ----
struct AptAllocateStringParameters {
    /* +0x00 */ const char* szFontName;
    /* +0x04 */ float x0;
    /* +0x08 */ float y0;
    /* +0x0c */ float x1;
    /* +0x10 */ float y1;
    /* +0x14 */ AptStringAlignment eAlignment;
    /* +0x18 */ AptStringAlignment eBoxAlignment;
    /* +0x1c */ int nMaxScroll;
    /* +0x20 */ float fStrLen;
    /* +0x24 */ int bMultiline;
    /* +0x28 */ int bWordWrap;
    /* +0x2c */ unsigned int nColour;
    /* +0x30 */ unsigned int nBackColor;
    /* +0x34 */ unsigned int nBorderColor;
    /* +0x38 */ int bBackground;
    /* +0x3c */ int bBorder;
    /* +0x40 */ float fTextWidth;
    /* +0x44 */ float fTextHeight;
    /* +0x48 */ float fFontHeight;
    /* +0x4c */ int nLineOffset;
    /* +0x50 */ int* pnNumLines;
    /* +0x54 */ const char* szString;
    /* +0x58 */ unsigned int eFlags;
    /* +0x5c */ void* pCurrString;
    /* +0x60 */ unsigned int nFontStyle;
    /* +0x64 */ int nIndent;
    /* +0x68 */ int nLeftMargin;
    /* +0x6c */ int nRightMargin;
};
// static_assert(sizeof(AptAllocateStringParameters) == 112);  // 32-bit console layout

// ---- AptCharacterBitmap  (sizeof = 4) ----
struct AptCharacterBitmap {
    /* +0x00 */ void* zID;
};
// static_assert(sizeof(AptCharacterBitmap) == 4);  // 32-bit console layout

// ---- AptArray  (sizeof = 44) ----
class AptArray : public AptObject {
    /* +0x20 */ AptValue** mpValues;
    /* +0x24 */ int mnCapacity;
    /* +0x28 */ int mnLength;
    // --- methods (address @ B4Extern) ---
    // 0x8249A8: int __cdecl AptArray::length()
    // 0x8249B0: AptValue* __cdecl AptArray::GetAt(const int nIndex)
    // 0x7C9D90: virtual AptValue* __cdecl AptArray::ConvertAptValue(AptValue* pValue) = 0
    // 0x84F940: virtual void __cdecl AptArray::CleanNativeFunctions() = 0
    // 0x84FB20: virtual void __cdecl AptArray::DestroyGCPointers()
    // 0x84FBC0: virtual void __cdecl AptArray::RegisterReferences()
    // 0x84FC60: void __cdecl AptArray::_reserve(int nSize)
    // 0x84FD28: void __cdecl AptArray::set(int nIndex, AptValue* pValue)
    // 0x84FDB8: AptValue* __cdecl AptArray::get(int nIndex)
    // 0x84FDF0: void __cdecl AptArray::toString(EAStringC& sBuf, const char* szSeparator)
    // 0x84FF98: virtual bool __cdecl AptArray::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue)
    // 0x850030: virtual AptValue* __cdecl AptArray::sMethod_pop(AptValue* pThis, int nParams) = 0
    // 0x8500E0: virtual AptValue* __cdecl AptArray::sMethod_shift(AptValue* pThis, int nParams) = 0
    // 0x8501C0: virtual int __cdecl AptArray::defaultSortCompareFunc(const void* a, const void* b) = 0
    // 0x8502B0: virtual int __cdecl AptArray::defaultSortOnCompareFunc(const void* a, const void* b) = 0
    // 0x8504D8: virtual AptValue* __cdecl AptArray::sMethod_reverse(AptValue* pThis, int nParams) = 0
    // 0x8505B0: virtual void __cdecl AptArray::~AptArray()
    // 0x8505F8: void __cdecl AptArray::toString(char* szBuf, const char* szSeparator)
    // 0x850698: virtual AptValue* __cdecl AptArray::sMethod_join(AptValue* pThis, int nParams) = 0
    // 0x8508E0: virtual int __cdecl AptArray::scriptFunctionSortFunc(const void* a, const void* b) = 0
    // 0x850A18: virtual AptValue* __cdecl AptArray::sMethod_sort(AptValue* pThis, int nParams) = 0
    // 0x850AE8: virtual AptValue* __cdecl AptArray::sMethod_sortOn(AptValue* pThis, int nParams) = 0
    // 0x850C08: virtual AptValue* __cdecl AptArray::sMethod_splice(AptValue* pThis, int nParams) = 0
    // 0x850EB8: void __cdecl AptArray::AptArray(int nElements, AptValue** pAptValue)
    // 0x851008: void __cdecl AptArray::AptArray()
    // 0x8510E8: virtual AptValue* __cdecl AptArray::sMethod_concat(AptValue* pThis, int nParams) = 0
    // 0x8513D0: virtual AptValue* __cdecl AptArray::sMethod_push(AptValue* pThis, int nParams) = 0
    // 0x851618: virtual AptValue* __cdecl AptArray::sMethod_unshift(AptValue* pThis, int nParams) = 0
    // 0x851848: virtual AptValue* __cdecl AptArray::sMethod_slice(AptValue* pThis, int nParams) = 0
    // 0x8519C0: virtual AptValue* __cdecl AptArray::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
};
// static_assert(sizeof(AptArray) == 44);  // 32-bit console layout

// ---- AptRect  (sizeof = 16) ----
struct AptRect {
    /* +0x00 */ float fLeft;
    /* +0x04 */ float fTop;
    /* +0x08 */ float fRight;
    /* +0x0c */ float fBottom;
};
// static_assert(sizeof(AptRect) == 16);  // 32-bit console layout

// ---- AptCIH  (sizeof = 96) ----
class AptCIH : public AptValueGC {
    /* +0x08 */ EAStringC mMyName;
    /* +0x0c */ AptMatrix matrix;
    /* +0x24 */ AptCXForm cxform;
    /* +0x44 */ AptCIH* pParent;
    /* +0x48 */ AptCharacterInst* pData;
    /* +0x4c */ AptCIH* pPrev;
    /* +0x50 */ AptCIH* pNext;
    /* +0x54 */ int nDepth : 17;
    /* +0x54 */ int nCreatedOnFrame : 14;
    /* +0x58 */ unsigned int nZombieCounter : 16;
    /* +0x58 */ unsigned int mbASChange : 1;
    /* +0x58 */ unsigned int mbHasClass : 1;
    /* +0x58 */ unsigned int mbIsZombie : 2;
    /* +0x58 */ unsigned int mbIsVisible : 1;
    /* +0x58 */ unsigned int mbInCtor : 1;
    /* +0x5c */ float* fRot;
    // --- methods (address @ B4Extern) ---
    // 0x8242E8: bool __cdecl AptCIH::IsInCtor()
    // 0x8242F8: void __cdecl AptCIH::SetInCtor(unsigned int bInCtor)
    // 0x828B58: bool __cdecl AptCIH::isAnimationInst(bool bUndefOK)
    // 0x8292F8: void __cdecl AptCIH::AptCIH(AptVirtualFunctionTable_Indices eType, AptCharacterInst* pInstData, AptCIH* _pParent)
    // 0x829418: virtual void __cdecl AptCIH::setHasClass(int bHasClass)
    // 0x829438: virtual int __cdecl AptCIH::getHasClass()
    // 0x84E1B0: bool __cdecl AptCIH::isSpriteInst(bool bUndefOK)
    // 0x84E210: bool __cdecl AptCIH::isShapeInst()
    // 0x84E258: bool __cdecl AptCIH::isMorphInst()
    // 0x84E2A0: bool __cdecl AptCIH::isLevelInst()
    // 0x84E2E8: bool __cdecl AptCIH::isSpriteInstBase(bool bUndefOK)
    // 0x873B70: bool __cdecl AptCIH::isTextInst()
    // 0x8790F0: virtual void __cdecl AptCIH::PreDestroy()
    // 0x879128: virtual void __cdecl AptCIH::DestroyGCPointers()
    // 0x8791C0: virtual AptValue* __cdecl AptCIH::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x8791D0: virtual bool __cdecl AptCIH::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue)
    // 0x8791E0: virtual void __cdecl AptCIH::Release()
    // 0x879208: void __cdecl AptCIH::getGlobalTranslation(float* pfX, float* pfY)
    // 0x879298: int __cdecl AptCIH::FindAndSetEvents()
    // 0x879360: void __cdecl AptCIH::SetEventHandler(int nEvent)
    // 0x8793A8: void __cdecl AptCIH::RemoveEventHandler(int nEvent)
    // 0x8793F0: int __cdecl AptCIH::HasEvent(int nEvent)
    // 0x879498: int __cdecl AptCIH::getParentCount()
    // 0x8794C0: int __cdecl AptCIH::getDepthOfParentAt(int nLvl)
    // 0x879520: bool __cdecl AptCIH::isParent(AptCIH* pParentTmp)
    // 0x879550: int __cdecl AptCIH::HasMouseEvent()
    // 0x879560: void __cdecl AptCIH::decZombieCount()
    // 0x879588: AptNativeHash* __cdecl AptCIH::getNativeHash()
    // 0x879600: virtual AptNativeHash* __cdecl AptCIH::GetNativeHashVirtual()
    // 0x879608: virtual bool __cdecl AptCIH::ContainsNativeHashVirtual()
    // 0x879640: void __cdecl AptCIH::deallocAssetStringRecursive()
    // 0x879730: void __cdecl AptCIH::_getBoundingRect(AptRenderingContext* pRenderingContext, AptRect* pRect)
    // 0x879890: void __cdecl AptCIH::getBoundingRect(AptRect* pRect)
    // 0x8798C0: void __cdecl AptCIH::getGlobalBoundingRect(AptRect* pRect)
    // 0x879980: float __cdecl AptCIH::GetProceduralProperty(AptProceduralProperty eProperty)
    // 0x879CB8: void __cdecl AptCIH::setProceduralProperty(AptProceduralProperty eProperty, float fValue, bool bASFlag)
    // 0x87A320: bool __cdecl AptCIH::queueClipEvents(int nEventFlags, unsigned int input, int bFromListenerSet)
    // 0x87A750: bool __cdecl AptCIH::checkIfHigher(AptCIH* pSptTmp)
    // 0x87A868: bool __cdecl AptCIH::isVisiable()
    // 0x87A8B8: AptCIH* __cdecl AptCIH::getRootAnimation()
    // 0x87A958: bool __cdecl AptCIH::hasRenderData()
    // 0x87AA68: void __cdecl AptCIH::GetMovieclipInfo(AptMovieclipInformation* pMCInfo)
    // 0x87AB70: void __cdecl AptCIH::ClearCIH(const bool bDestroyGC)
    // 0x87AFE8: virtual void __cdecl AptCIH::RegisterReferences()
    // 0x87B0B8: void __cdecl AptCIH::ensureStringAllocated(AptCIH* pParent)
    // 0x87B3E8: void __cdecl AptCIH::render(AptRenderingContext* pRenderingContext, AptMath::ClipTransform_t* pTransform, AptMaskRenderOperation eMaskOperation)
    // 0x87BA18: virtual void __cdecl AptCIH::~AptCIH()
    // 0x87BAD0: void __cdecl AptCIH::Remove()
    // 0x87BB88: void __cdecl AptCIH::jumpToFrame(int nTargetFrame)
    // 0x87BCD0: void __cdecl AptCIH::tick()
    // 0x87BE60: void __cdecl AptCIH::associateInstToClass()
    // 0x879088: virtual float __cdecl AptCIH::GetVectorLength(const AptMatrix* matrix) = 0
    // 0x87C2A0: bool __cdecl AptCIH::isStaticTextInst()
    // 0x87C2E8: virtual float __cdecl AptCIH::GetCosAngle(const AptMatrix* matrix) = 0
};
// static_assert(sizeof(AptCIH) == 96);  // 32-bit console layout

// ---- AptValueNoGC  (sizeof = 8) ----
class AptValueNoGC : public AptValue {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptValueNoGC) == 8);  // 32-bit console layout

// ---- AptHashItem  (sizeof = 8) ----
struct AptHashItem {
    /* +0x00 */ EAStringC Key;
    /* +0x04 */ AptValue* mValue;
};
// static_assert(sizeof(AptHashItem) == 8);  // 32-bit console layout

// ---- AptLookup  (sizeof = 12) ----
class AptLookup : public AptValueNoGC {
    /* +0x08 */ int nLookup;
    // --- methods (address @ B4Extern) ---
    // 0x84E890: void __cdecl AptLookup::AptLookup(int _nLookup)
};
// static_assert(sizeof(AptLookup) == 12);  // 32-bit console layout

// ---- AptLoadVars  (sizeof = 36) ----
class AptLoadVars : public AptObject {
    /* +0x20 */ int iIsLoaded;
    // --- methods (address @ B4Extern) ---
    // 0x84F090: void __cdecl AptLoadVars::AptLoadVars()
    // 0x862708: virtual void __cdecl AptLoadVars::CleanNativeFunctions() = 0
    // 0x862BD8: virtual void __cdecl AptLoadVars::~AptLoadVars()
    // 0x862C20: virtual AptValue* __cdecl AptLoadVars::sMethod_toString(AptValue* pThis, int nParams) = 0
    // 0x8664F0: virtual AptValue* __cdecl AptLoadVars::sMethod_load(AptValue* pThis, int nParams) = 0
    // 0x866A78: virtual AptValue* __cdecl AptLoadVars::sMethod_send(AptValue* pThis, int nParams) = 0
    // 0x866EA8: virtual AptValue* __cdecl AptLoadVars::sMethod_sendAndLoad(AptValue* pThis, int nParams) = 0
    // 0x8675E0: virtual AptValue* __cdecl AptLoadVars::sMethod_getBytesTotal(AptValue* pThis, int nParams) = 0
    // 0x867778: virtual AptValue* __cdecl AptLoadVars::sMethod_getBytesLoaded(AptValue* pThis, int nParams) = 0
    // 0x869FF8: virtual AptValue* __cdecl AptLoadVars::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
};
// static_assert(sizeof(AptLoadVars) == 36);  // 32-bit console layout

// ---- AptControlRemoveObject2  (sizeof = 4) ----
struct AptControlRemoveObject2 {
    /* +0x00 */ int nDepth;
};
// static_assert(sizeof(AptControlRemoveObject2) == 4);  // 32-bit console layout

// ---- AptDate  (sizeof = 32) ----
class AptDate : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x828BB8: virtual void __cdecl AptDate::~AptDate()
    // 0x84EC80: void __cdecl AptDate::AptDate(int year, int month, int date, int hour, int minute, int second, int millisecond)
    // 0x8755D8: virtual void __cdecl AptDate::CleanNativeFunctions() = 0
};
// static_assert(sizeof(AptDate) == 32);  // 32-bit console layout

// ---- AptLoader  (sizeof = 4) ----
struct AptLoader {
    /* +0x00 */ CommonSense::SingleList::SingleList<AptFile *,AptSingleListPolicy> mFiles;
    // --- methods (address @ B4Extern) ---
    // 0x829BB8: void __cdecl AptLoader::GetFileVector(AptSharedPtr<AptFile>* aFilePtrs, int nMaxSize)
    // 0x852348: void __cdecl AptLoader::Invalidate(AptFile* pFile)
    // 0x852470: AptSharedPtr<AptFile> __cdecl AptLoader::findFile(EAStringC& sFilename)
    // 0x852510: AptSharedPtr<AptFile> __cdecl AptLoader::IsLoaded(EAStringC& sFilename)
    // 0x8525A0: AptSharedPtr<AptFile> __cdecl AptLoader::Load(EAStringC& sFilename)
    // 0x8526C0: bool __cdecl AptLoader::AllImportsAvailable(AptSharedPtr<AptFile>* f)
    // 0x8528B8: void __cdecl AptLoader::CompleteLoad(AptSharedPtr<AptFile>* f, void* pData, void* pConstTable, void* pUserData)
    // 0x852968: void __cdecl AptLoader::CancelPreloadedAnimation(EAStringC& sFilename)
    // 0x852BD0: void __cdecl AptLoader::~AptLoader()
    // 0x852E98: void __cdecl AptLoader::notify(AptSharedPtr<AptFile>* f)
    // 0x852F28: void __cdecl AptLoader::Update()
};
// static_assert(sizeof(AptLoader) == 4);  // 32-bit console layout

// ---- AptStringObject  (sizeof = 36) ----
class AptStringObject : public AptObject {
    /* +0x20 */ AptString* mpStringObject;
    // --- methods (address @ B4Extern) ---
    // 0x84E918: void __cdecl AptStringObject::AptStringObject(AptString* pString)
    // 0x84EA10: virtual AptValue* __cdecl AptStringObject::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x84EA60: virtual void __cdecl AptStringObject::~AptStringObject()
};
// static_assert(sizeof(AptStringObject) == 36);  // 32-bit console layout

// ---- AptPrototype  (sizeof = 32) ----
class AptPrototype : public AptValueWithHash {
    /* +0x1c */ AptValue* mp__constructor__;
    // --- methods (address @ B4Extern) ---
    // 0x856798: virtual void __cdecl AptPrototype::DestroyGCPointers()
    // 0x8567F0: virtual void __cdecl AptPrototype::RegisterReferences()
    // 0x824688: AptValue* __cdecl AptPrototype::GetSuperConstructor()
    // 0x824690: void __cdecl AptPrototype::SetSuperConstructor(AptValue* pNewSuperConstructor)
    // 0x82FB10: void __cdecl AptPrototype::AptPrototype()
    // 0x82FB88: virtual AptValue* __cdecl AptPrototype::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x82FBE0: virtual bool __cdecl AptPrototype::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue)
};
// static_assert(sizeof(AptPrototype) == 32);  // 32-bit console layout

// ---- AptKey  (sizeof = 32) ----
class AptKey : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x828BB8: virtual void __cdecl AptKey::~AptKey()
    // 0x8625A0: virtual void __cdecl AptKey::CleanNativeFunctions() = 0
    // 0x862AB8: virtual AptValue* __cdecl AptKey::sMethod_addListener(AptValue* pThis, int nParams) = 0
    // 0x864EF0: virtual AptValue* __cdecl AptKey::sMethod_isDown(AptValue* pThis, int nParams) = 0
    // 0x8651C8: virtual AptValue* __cdecl AptKey::sMethod_isToggled(AptValue* pThis, int nParams) = 0
    // 0x865320: virtual AptValue* __cdecl AptKey::sMethod_getCode(AptValue* pThis, int nParams) = 0
    // 0x8654C8: virtual AptValue* __cdecl AptKey::sMethod_getAscii(AptValue* pThis, int nParams) = 0
    // 0x8657A8: virtual AptValue* __cdecl AptKey::sMethod_getController(AptValue* pThis, int nParams) = 0
    // 0x865920: virtual AptValue* __cdecl AptKey::sMethod_removeListener(AptValue* pThis, int nParams) = 0
    // 0x865D40: virtual AptValue* __cdecl AptKey::sMethod_getAnalogStickInfo(AptValue* pThis, int nParams) = 0
    // 0x8688E8: virtual AptValue* __cdecl AptKey::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x830098: void __cdecl AptKey::AptKey()
};
// static_assert(sizeof(AptKey) == 32);  // 32-bit console layout

// ---- AptSavedInputRecord  (sizeof = 4) ----
struct AptSavedInputRecord {
    /* +0x00 */ unsigned int nTick;
};
// static_assert(sizeof(AptSavedInputRecord) == 4);  // 32-bit console layout

// ---- AptMatrix  (sizeof = 24) ----
struct AptMatrix {
    /* +0x00 */ float a;
    /* +0x04 */ float b;
    /* +0x08 */ float c;
    /* +0x0c */ float d;
    /* +0x10 */ float tx;
    /* +0x14 */ float ty;
};
// static_assert(sizeof(AptMatrix) == 24);  // 32-bit console layout

// ---- AptLinker  (sizeof = 24) ----
struct AptLinker {
    /* +0x00 */ CommonSense::SingleList::SingleList<AptSharedPtr<AptLinkerThingy>,AptSingleListPolicy> mThingys;
    /* +0x04 */ EA::String::BasicString<StringAsVectorEncoding<AptSharedPtr<AptFile> >,StringAsVectorPolicy> mLoadedFilesWaitingForLink;
    // --- methods (address @ B4Extern) ---
    // 0x852CB0: void __cdecl AptLinker::Notify(AptSharedPtr<AptFile>* f)
    // 0x8530C8: void __cdecl AptLinker::Update()
    // 0x853550: void __cdecl AptLinker::SwapOut(AptSharedPtr<AptFile>* f1, AptSharedPtr<AptFile>* f2)
    // 0x853810: void __cdecl AptLinker::Load(EAStringC& sFilename, EAStringC* sTarget)
    // 0x853F10: void __cdecl AptLinker::CancelLoad(AptCIH* pCIH)
    // 0x8547E8: CommonSense::SingleList::SingleList<AptSharedPtr<AptLinkerThingy>,AptSingleListPolicy>::Iterator __cdecl AptLinker::findThingy(AptSharedPtr<AptFile>* pFile)
    // 0x8548D8: int __cdecl AptLinker::isFileImported(AptSharedPtr<AptFile>* pFile)
};
// static_assert(sizeof(AptLinker) == 24);  // 32-bit console layout

// ---- AptXml  (sizeof = 32) ----
class AptXml : public AptXmlNode {
    // --- methods (address @ B4Extern) ---
    // 0x873FD0: virtual void __cdecl AptXml::~AptXml()
    // 0x873FE0: virtual void __cdecl AptXml::CleanNativeFunctions() = 0
};
// static_assert(sizeof(AptXml) == 32);  // 32-bit console layout

// ---- AptXmlAttributes  (sizeof = 32) ----
class AptXmlAttributes : public AptObject {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptXmlAttributes) == 32);  // 32-bit console layout

// ---- AptIntervalTimer  (sizeof = 32) ----
struct AptIntervalTimer {
    /* +0x00 */ int bValid;
    /* +0x04 */ AptValue* pCBFunction;
    /* +0x08 */ float fInterval;
    /* +0x0c */ float fCurTime;
    /* +0x10 */ AptValue* pContext;
    /* +0x14 */ AptValuePtrStack<AptValue> pParams;
    // --- methods (address @ B4Extern) ---
    // 0x84E3B0: void __cdecl AptIntervalTimer::cleanParams()
};
// static_assert(sizeof(AptIntervalTimer) == 32);  // 32-bit console layout

// ---- AptMovieclipInformation  (sizeof = 28) ----
struct AptMovieclipInformation {
    /* +0x00 */ int nAnimations;
    /* +0x04 */ int nMovieClips;
    /* +0x08 */ int nButtons;
    /* +0x0c */ int nStaticText;
    /* +0x10 */ int nDynamicText;
    /* +0x14 */ int nMorph;
    /* +0x18 */ int nShapes;
};
// static_assert(sizeof(AptMovieclipInformation) == 28);  // 32-bit console layout

// ---- AptAction_TryCatchFinallyBlock  (sizeof = 20) ----
struct AptAction_TryCatchFinallyBlock {
    /* +0x00 */ unsigned int uTryCodeSize;
    /* +0x04 */ unsigned int uCatchCodeSize;
    /* +0x08 */ unsigned int uFinallyCodeSize;
    /* +0x0c */ unsigned char uFlags;
    /* +0x0d */ unsigned char uAlignment1;
    /* +0x0e */ unsigned char uAlignment2;
    /* +0x0f */ unsigned char uCaughtRegister;
    /* +0x10 */ char* szCaughtVarName;
};
// static_assert(sizeof(AptAction_TryCatchFinallyBlock) == 20);  // 32-bit console layout

// ---- AptAction_DefineFunction2  (sizeof = 28) ----
struct AptAction_DefineFunction2 {
    /* +0x00 */ const char* szName;
    /* +0x04 */ int nParams;
    /* +0x08 */ short nRegisterCount;
    /* +0x0a */ short nFlags;
    /* +0x0c */ AptRegisterParam* aszParams;
    /* +0x10 */ int nCodeSize;
    /* +0x14 */ AptConstantPool constantPool;
};
// static_assert(sizeof(AptAction_DefineFunction2) == 28);  // 32-bit console layout

// ---- AptSavedInputCheckpoints  (sizeof = 28) ----
struct AptSavedInputCheckpoints {
    /* +0x00 */ EA::String::BasicString<StringAsVectorEncoding<AptFileSavedInputState>,StringAsVectorPolicy> mPending;
    // --- methods (address @ B4Extern) ---
    // 0x82A208: bool __cdecl AptSavedInputCheckpoints::allStatesAre2(AptFileSavedInputState::State state0, AptFileSavedInputState::State state1)
    // 0x82A6F8: void __cdecl AptSavedInputCheckpoints::Checkpoint(EAStringC& s)
    // 0x8549F8: void __cdecl AptSavedInputCheckpoints::updateState(EAStringC& name, AptFileSavedInputState::State lookFor, AptFileSavedInputState::State setTo, AptFileSavedInputState::State ifNotFound)
};
// static_assert(sizeof(AptSavedInputCheckpoints) == 28);  // 32-bit console layout

// ---- AptActionBlock  (sizeof = 4) ----
struct AptActionBlock {
    /* +0x00 */ unsigned char* aActionStream;
};
// static_assert(sizeof(AptActionBlock) == 4);  // 32-bit console layout

// ---- AptInteger  (sizeof = 12) ----
class AptInteger : public AptValueNoGC {
    /* +0x08 */ int mnValue;
    /* +0x08 */ AptInteger* mpNextFree;
    // --- methods (address @ B4Extern) ---
    // 0x85CF28: virtual void __cdecl AptInteger::ClearPool() = 0
    // 0x85CFA8: virtual void __cdecl AptInteger::DeleteThis()
    // 0x85CFC0: virtual void __cdecl AptInteger::ForceDelete()
    // 0x8251F8: void __cdecl AptInteger::Destroy()
    // 0x825210: int __cdecl AptInteger::GetInt()
};
// static_assert(sizeof(AptInteger) == 12);  // 32-bit console layout

// ---- AptDisplayListState  (sizeof = 4) ----
struct AptDisplayListState {
    /* +0x00 */ AptCIH* pHead;
    // --- methods (address @ B4Extern) ---
    // 0x8757C0: void __cdecl AptDisplayListState::findInst(int nDepth, EAStringC* pName, AptCIH** ppPrev, AptCIH** ppItem)
    // 0x875918: int __cdecl AptDisplayListState::getLength()
    // 0x875940: AptCIH* __cdecl AptDisplayListState::getValue(int nIndex)
    // 0x875970: void __cdecl AptDisplayListState::RegisterReferences(AptValue* pFrom)
    // 0x8759F0: virtual AptCIH* __cdecl AptDisplayListState::remove(AptCIH* pItem) = 0
    // 0x875D60: bool __cdecl AptDisplayListState::hasRenderData()
    // 0x875DD0: void __cdecl AptDisplayListState::GetMovieclipInfo(AptMovieclipInformation* pMCInfo)
    // 0x875E28: void __cdecl AptDisplayListState::~AptDisplayListState()
    // 0x875F58: AptCIH* __cdecl AptDisplayListState::insert(AptCIH* pPrev, AptCIH* pNewItem)
    // 0x875FC0: AptCIH* __cdecl AptDisplayListState::insert(int nDepth, AptCIH* pItem)
    // 0x876070: AptCIH* __cdecl AptDisplayListState::insert(int nDepth, AptCIH* pItem, AptCIH* pPrev, AptCIH* pItemAtDepth)
    // 0x8760F0: AptCIH* __cdecl AptDisplayListState::remove(int nDepth)
    // 0x876E78: AptCIH* __cdecl AptDisplayListState::insert(int nDepth, AptVirtualFunctionTable_Indices eType, AptCharacterInst* pInst, AptCIH* pPrev, AptCIH* pItemAtDepth)
    // 0x876F20: AptCIH* __cdecl AptDisplayListState::insert(int nDepth, AptVirtualFunctionTable_Indices eType, AptCharacterInst* pInst)
    // 0x877B48: void __cdecl AptDisplayListState::AptDisplayListState()
};
// static_assert(sizeof(AptDisplayListState) == 4);  // 32-bit console layout

// ---- AptRegister  (sizeof = 12) ----
class AptRegister : public AptValueNoGC {
    /* +0x08 */ int nVal;
    // --- methods (address @ B4Extern) ---
    // 0x84E7B0: void __cdecl AptRegister::AptRegister(int _nVal)
};
// static_assert(sizeof(AptRegister) == 12);  // 32-bit console layout

// ---- AptScriptFunctionByteCodeBlock  (sizeof = 68) ----
class AptScriptFunctionByteCodeBlock : public AptScriptFunctionBase {
    /* +0x30 */ const unsigned char* mpByteCodeBase;
    /* +0x34 */ const int mnByteCodeSize;
    /* +0x38 */ const char* mpName;
    /* +0x3c */ AptConstantPool mConstantPool;
    // --- methods (address @ B4Extern) ---
    // 0x85E568: void __cdecl AptScriptFunctionByteCodeBlock::AptScriptFunctionByteCodeBlock(const unsigned char* pBytecodeBase, int blockSize, AptConstantPool constantPool, const char* pName, AptCIH* pCurCIH, AptScriptFunctionBase* pCreatorFunction)
    // 0x880E88: virtual const char* __cdecl AptScriptFunctionByteCodeBlock::GetName()
    // 0x79B3B0: virtual unsigned int __cdecl AptScriptFunctionByteCodeBlock::GetNumArguments()
    // 0x88F1E8: virtual const unsigned char* __cdecl AptScriptFunctionByteCodeBlock::GetByteCodeBase()
    // 0x88F1F0: virtual unsigned int __cdecl AptScriptFunctionByteCodeBlock::GetByteCodeSize()
    // 0x85E8C8: virtual AptConstantPool __cdecl AptScriptFunctionByteCodeBlock::GetConstantPool()
    // 0x7C9D90: virtual void __cdecl AptScriptFunctionByteCodeBlock::SetArgument(AptValue* pValue, int nIndex)
    // 0x79B3B0: virtual AptScriptFunctionBase* __cdecl AptScriptFunctionByteCodeBlock::Duplicate(AptCIH* pCurCIH)
};
// static_assert(sizeof(AptScriptFunctionByteCodeBlock) == 68);  // 32-bit console layout

// ---- AptCharacterMorph  (sizeof = 8) ----
struct AptCharacterMorph {
    /* +0x00 */ AptCharacter* pStartCharacter;
    /* +0x04 */ AptCharacter* pEndCharacter;
};
// static_assert(sizeof(AptCharacterMorph) == 8);  // 32-bit console layout

// ---- AptValueWithHash  (sizeof = 28) ----
class AptValueWithHash : public AptValueGC {
    /* +0x08 */ AptNativeHash mNativeHash;
    // --- methods (address @ B4Extern) ---
    // 0x82DAB0: virtual AptNativeHash* __cdecl AptValueWithHash::GetNativeHashVirtual()
    // 0x82DAB8: virtual bool __cdecl AptValueWithHash::ContainsNativeHashVirtual()
    // 0x82DAC0: virtual void __cdecl AptValueWithHash::RegisterReferences()
    // 0x82DAD0: virtual void __cdecl AptValueWithHash::DestroyGCPointers()
};
// static_assert(sizeof(AptValueWithHash) == 28);  // 32-bit console layout

// ---- AptCharacterTextInst  (sizeof = 120) ----
struct AptCharacterTextInst : public AptCharacterInst {
    /* +0x18 */ EAStringC mTextValue;
    /* +0x1c */ EAStringC mVarValue;
    /* +0x20 */ void* zID;
    /* +0x24 */ unsigned int nColour;
    /* +0x28 */ int nMaxScroll;
    /* +0x2c */ int nScroll;
    /* +0x30 */ unsigned int nBackColor;
    /* +0x34 */ unsigned int nBorderColor;
    /* +0x38 */ AptStringAlignment eBoxAlignment;
    /* +0x3c */ AptStringAlignment eAlignment;
    /* +0x40 */ int nMaxChars;
    /* +0x44 */ float fTextWidth;
    /* +0x48 */ float fTextHeight;
    /* +0x4c */ float fLength;
    /* +0x50 */ AptRect rBounds;
    /* +0x60 */ float fFontSize;
    /* +0x64 */ int nFontID;
    /* +0x68 */ TextFormat* pMyTextFormat;
    /* +0x6c */ unsigned int eFlags;
    /* +0x70 */ unsigned int nFontStyle;
    /* +0x74 */ unsigned int bCreatedDynamic : 1;
    /* +0x74 */ unsigned int bBorder : 1;
    /* +0x74 */ unsigned int bBackground : 1;
    /* +0x74 */ unsigned int bMouseWheelEnabled : 1;
    // --- methods (address @ B4Extern) ---
    // 0x86BD90: void __cdecl AptCharacterTextInst::SetText(const AptCIH* pParent)
    // 0x86C108: void __cdecl AptCharacterTextInst::UpdateText(const AptCIH* pParent)
    // 0x86C410: void __cdecl AptCharacterTextInst::AptCharacterTextInst()
    // 0x86ED80: virtual void __cdecl AptCharacterTextInst::~AptCharacterTextInst()
};
// static_assert(sizeof(AptCharacterTextInst) == 120);  // 32-bit console layout

// ---- AptStage  (sizeof = 32) ----
class AptStage : public AptObject {
    // --- methods (address @ B4Extern) ---
    // 0x828BB8: virtual void __cdecl AptStage::~AptStage()
    // 0x862A20: virtual void __cdecl AptStage::CleanNativeFunctions() = 0
    // 0x862A98: virtual AptValue* __cdecl AptStage::sMethod_addListener(AptValue* pThis, int nParams) = 0
    // 0x862AA8: virtual AptValue* __cdecl AptStage::sMethod_removeListener(AptValue* pThis, int nParams) = 0
    // 0x867C28: virtual AptValue* __cdecl AptStage::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x830350: void __cdecl AptStage::AptStage()
};
// static_assert(sizeof(AptStage) == 32);  // 32-bit console layout

// ---- AptCharacterStaticTextInst  (sizeof = 24) ----
struct AptCharacterStaticTextInst : public AptCharacterInst {
    // (no direct members; see bases / raw dump)
};
// static_assert(sizeof(AptCharacterStaticTextInst) == 24);  // 32-bit console layout

// ---- AptNone  (sizeof = 8) ----
class AptNone : public AptValueNoGC {
    // --- methods (address @ B4Extern) ---
    // 0x5A93C8: virtual void __cdecl AptNone::~AptNone()
    // 0x82FD20: void __cdecl AptNone::AptNone()
    // 0x7C9D90: virtual void __cdecl AptNone::AddRef()
    // 0x7C9D90: virtual void __cdecl AptNone::Release()
};
// static_assert(sizeof(AptNone) == 8);  // 32-bit console layout

// ---- AptAnimationPoolData  (sizeof = 144) ----
struct AptAnimationPoolData {
    /* +0x00 */ AptCIH** apNewInsts;
    /* +0x04 */ int nNewInsts;
    /* +0x08 */ AptValueSet<AptValue *> listenerSet;
    /* +0x10 */ AptValueSet<AptCIH *> inputSet;
    /* +0x18 */ AptDisplayList displayList;
    /* +0x1c */ AptIntervalTimer* aIntervalTimers;
    /* +0x20 */ int nIntervalTimers;
    /* +0x24 */ int nQueuedInputs;
    /* +0x28 */ unsigned int* aQueuedInputs;
    /* +0x2c */ AptValue* pDragMC;
    /* +0x30 */ AptMatrix mDragPos;
    /* +0x48 */ AptValue* pOnPress;
    /* +0x4c */ AptValue* pOnRollOver;
    /* +0x50 */ AptValue* pTopMostSprite;
    /* +0x54 */ int nXMousePos;
    /* +0x58 */ int nYMousePos;
    /* +0x5c */ AptAnalogStickInfo gAStickLeft;
    /* +0x6c */ AptAnalogStickInfo gAStickRight;
    /* +0x7c */ AptCIH* pInputMask;
    /* +0x80 */ AptActionQueueC* m_pAptActionPool;
    /* +0x84 */ int m_iMaxNewMovieClips;
    /* +0x88 */ int m_iMaxIntervalTimers;
    /* +0x8c */ int m_iMaxQueuedInputs;
    // --- methods (address @ B4Extern) ---
    // 0x824A90: AptActionQueueC* __cdecl AptAnimationPoolData::GetActionPool()
    // 0x828C30: void __cdecl AptAnimationPoolData::addActionBack(AptActionBlock* pActionBlock, AptCIH* pCIH, unsigned int input)
    // 0x828C38: void __cdecl AptAnimationPoolData::addActionFront(AptActionBlock* pActionBlock, AptCIH* pCIH, unsigned int input)
    // 0x828C40: void __cdecl AptAnimationPoolData::addFunctionBack(AptCIH* pContext, AptValue* pFuncDef, int nParams, unsigned int input)
    // 0x828C48: void __cdecl AptAnimationPoolData::addFunctionFront(AptCIH* pContext, AptValue* pFuncDef, int nParams, unsigned int input)
    // 0x85EAD0: void __cdecl AptAnimationPoolData::Reset()
    // 0x85EB18: void __cdecl AptAnimationPoolData::addInput(unsigned int nInput)
    // 0x85EBB8: void __cdecl AptAnimationPoolData::addInput(AptInputType eType, AptInputState eState, AptInputController eController)
    // 0x85EBD0: void __cdecl AptAnimationPoolData::setInputMask(AptCIH* pMask)
    // 0x85EBD8: bool __cdecl AptAnimationPoolData::isInputMasked(AptCIH* pObj)
    // 0x85F448: void __cdecl AptAnimationPoolData::PreDestroy()
    // 0x85F570: void __cdecl AptAnimationPoolData::tickIntervalTimers(int nMilliseconds)
    // 0x85F838: void __cdecl AptAnimationPoolData::_tickNewInsts()
    // 0x85F900: void __cdecl AptAnimationPoolData::addAnalogInput(AptAnalogStickInfo pInput)
    // 0x85F980: void __cdecl AptAnimationPoolData::removeTimerFunctions(AptCIH* pAnimCIH)
    // 0x85FC30: void __cdecl AptAnimationPoolData::RegisterReferences()
    // 0x860D60: void __cdecl AptAnimationPoolData::AptAnimationPoolData(AptInitParmsT& aptInitParms)
    // 0x860F88: void __cdecl AptAnimationPoolData::~AptAnimationPoolData()
    // 0x861020: void __cdecl AptAnimationPoolData::runActions()
    // 0x8789E0: bool __cdecl AptAnimationPoolData::_pointHits(AptCIH* pSprInst, unsigned int input)
    // 0x878A90: void __cdecl AptAnimationPoolData::ProcessInputSet(AptInputType eType, AptInputState eState, unsigned int input, AptInputController eController, bool bCheckTop)
    // 0x878BD8: void __cdecl AptAnimationPoolData::AddListenerToQueue(AptValue* pValue, int nEventFlags, unsigned int input)
    // 0x878E78: void __cdecl AptAnimationPoolData::ProcessListenerEvents(AptInputType eType, AptInputState eState, unsigned int input, AptInputController eController)
    // 0x878F20: void __cdecl AptAnimationPoolData::ProcessAptInput(unsigned int input, bool bCheck)
    // 0x878F78: void __cdecl AptAnimationPoolData::ProcessInputs()
};
// static_assert(sizeof(AptAnimationPoolData) == 144);  // 32-bit console layout

// ---- AptInitParmsT  (sizeof = 60) ----
struct AptInitParmsT {
    /* +0x00 */ int iButtonSetSize;
    /* +0x04 */ int iInputSetSize;
    /* +0x08 */ int iListenerSetSize;
    /* +0x0c */ int iActionPoolSize;
    /* +0x10 */ int iMaxIntervalFunctions;
    /* +0x14 */ int iMaxButtonInstances;
    /* +0x18 */ int iMaxNewMovieClipsPerFrame;
    /* +0x1c */ int iMaxQueuedInputs;
    /* +0x20 */ int iStackSize;
    /* +0x24 */ int iCallStackDepth;
    /* +0x28 */ int iDeferedVectorSize;
    /* +0x2c */ int iStringPoolSize;
    /* +0x30 */ int iRegArraySize;
    /* +0x34 */ int iZombieVectorSize;
    /* +0x38 */ bool bDefaultMouseWheelFlag;
    /* +0x39 */ bool bPrintZombieDump;
};
// static_assert(sizeof(AptInitParmsT) == 60);  // 32-bit console layout

// ---- AptCharacterInst  (sizeof = 24) ----
struct AptCharacterInst {
    /* +0x00 */ void* __vftable;
    /* +0x04 */ int nClipDepth;
    /* +0x08 */ int nCreatedOnFrame;
    /* +0x0c */ AptCharacter* pCharacter;
    /* +0x10 */ AptNativeHash* mpNativeHash;
    /* +0x14 */ bool mbGCPointersDestroyed;
    // --- methods (address @ B4Extern) ---
    // 0x861590: virtual void __cdecl AptCharacterInst::DestroyGCPointers()
    // 0x86B4A8: virtual void __cdecl AptCharacterInst::CleanNativeFunctions() = 0
    // 0x86B908: virtual AptValue* __cdecl AptCharacterInst::sMethod_unloadMovie(AptValue* pThis, int nParams) = 0
    // 0x86BA08: virtual AptValue* __cdecl AptCharacterInst::sMethod_removeMovieClip(AptValue* pThis, int nParams) = 0
    // 0x86BAB8: virtual AptValue* __cdecl AptCharacterInst::sMethod_removeTextField(AptValue* pThis, int nParams) = 0
    // 0x86BB68: virtual AptValue* __cdecl AptCharacterInst::sMethod_nextFrame(AptValue* pThis, int nParams) = 0
    // 0x86BBB8: virtual AptValue* __cdecl AptCharacterInst::sMethod_prevFrame(AptValue* pThis, int nParams) = 0
    // 0x86C4D0: virtual AptValue* __cdecl AptCharacterInst::_gotoAndX(AptValue* pThis, int nParams, int bPlay) = 0
    // 0x86C638: virtual AptValue* __cdecl AptCharacterInst::sMethod_gotoAndStop(AptValue* pThis, int nParams) = 0
    // 0x86C640: virtual AptValue* __cdecl AptCharacterInst::sMethod_gotoAndPlay(AptValue* pThis, int nParams) = 0
    // 0x86C648: virtual AptValue* __cdecl AptCharacterInst::sMethod_attachMovie(AptValue* pThis, int nParams) = 0
    // 0x86C838: virtual AptValue* __cdecl AptCharacterInst::sMethod_loadMovie(AptValue* pThis, int nParams) = 0
    // 0x86CA08: virtual AptValue* __cdecl AptCharacterInst::sMethod_duplicateMovieClip(AptValue* pThis, int nParams) = 0
    // 0x86CA90: virtual AptValue* __cdecl AptCharacterInst::sMethod_createTextField(AptValue* pThis, int nParams) = 0
    // 0x86CDA8: virtual AptValue* __cdecl AptCharacterInst::sMethod_swapDepths(AptValue* pThis, int nParams) = 0
    // 0x86D1E8: virtual AptValue* __cdecl AptCharacterInst::sMethod_setMask(AptValue* pThis, int nParams) = 0
    // 0x86D330: virtual AptValue* __cdecl AptCharacterInst::sMethod_startDrag(AptValue* pThis, int nParams) = 0
    // 0x86D4C8: virtual AptValue* __cdecl AptCharacterInst::sMethod_createEmptyMovieClip(AptValue* pThis, int nParams) = 0
    // 0x86D668: virtual AptValue* __cdecl AptCharacterInst::sMethod_loadVariables(AptValue* pThis, int nParams) = 0
    // 0x86D730: virtual AptValue* __cdecl AptCharacterInst::sMethod_stop(AptValue* pThis, int nParams) = 0
    // 0x86D788: virtual AptValue* __cdecl AptCharacterInst::sMethod_play(AptValue* pThis, int nParams) = 0
    // 0x86D7E0: virtual bool __cdecl AptCharacterInst::objectMemberSet(const AptValue* pContext, const EAStringC* pName, const AptValue* pValue) = 0
    // 0x86EF00: virtual AptValue* __cdecl AptCharacterInst::sMethod_getDepth(AptValue* pThis, int nParams) = 0
    // 0x86F0E8: virtual AptValue* __cdecl AptCharacterInst::sMethod_getBounds(AptValue* pThis, int nParams) = 0
    // 0x86F638: virtual AptValue* __cdecl AptCharacterInst::sMethod_hitTest(AptValue* pThis, int nParams) = 0
    // 0x86FCF0: virtual AptValue* __cdecl AptCharacterInst::sMethod_getBytesTotal(AptValue* pThis, int nParams) = 0
    // 0x8700F0: virtual AptValue* __cdecl AptCharacterInst::sMethod_getBytesLoaded(AptValue* pThis, int nParams) = 0
    // 0x8703C0: virtual AptValue* __cdecl AptCharacterInst::sMethod_setTextFormat(AptValue* pThis, int nParams) = 0
    // 0x870600: virtual AptValue* __cdecl AptCharacterInst::sMethod_getNewTextFormat(AptValue* pThis, int nParams) = 0
    // 0x870860: virtual AptValue* __cdecl AptCharacterInst::sMethod_getTextFormat(AptValue* pThis, int nParams) = 0
    // 0x870C80: virtual AptValue* __cdecl AptCharacterInst::sMethod_localToGlobal(AptValue* pThis, int nParams) = 0
    // 0x870FE8: virtual AptValue* __cdecl AptCharacterInst::objectMemberLookup(const AptValue* pContext, const EAStringC* pName) = 0
    // 0x7C9D90: virtual void __cdecl AptCharacterInst::PreDestroy()
};
// static_assert(sizeof(AptCharacterInst) == 24);  // 32-bit console layout

// ---- AptObject  (sizeof = 32) ----
class AptObject : public AptValueWithHash {
    /* +0x1c */ unsigned int mnImplementedObjects : 8;
    /* +0x1c */ unsigned int mbHasClass : 1;
    /* +0x1c */ unsigned int mbIsInMainInst : 1;
    // --- methods (address @ B4Extern) ---
    // 0x856870: virtual AptValue* __cdecl AptObject::objectMemberLookup(const AptValue* pContext, const EAStringC* pName)
    // 0x8568C8: virtual void __cdecl AptObject::RegisterReferences()
    // 0x8568D0: virtual void __cdecl AptObject::DestroyGCPointers()
    // 0x8568D8: void __cdecl AptObject::SetImplementedObjects(AptArray* paImplementedObjects, int nNumObjects)
    // 0x856950: AptArray* __cdecl AptObject::GetImplementedObjects(int* nOutNumObjects)
    // 0x856A00: bool __cdecl AptObject::DoesImplementObject(AptValue* pPrototype)
    // 0x825238: void __cdecl AptObject::Set(const EAStringC* pKey, const AptValue* pValue)
    // 0x825240: AptValue* __cdecl AptObject::Lookup(const EAStringC* pKey)
    // 0x8246F8: void __cdecl AptObject::Set__Proto__(const AptValue* pValue)
    // 0x824768: void __cdecl AptObject::SetPrototype(const AptValue* pValue)
};
// static_assert(sizeof(AptObject) == 32);  // 32-bit console layout

// ---- AptDisplayList  (sizeof = 4) ----
struct AptDisplayList {
    /* +0x00 */ AptDisplayListState* pState;
    // --- methods (address @ B4Extern) ---
    // 0x875AF8: void __cdecl AptDisplayList::removeObject(AptCIH* pItem)
    // 0x875BF8: void __cdecl AptDisplayList::removeObject(int nRemovalDepth)
    // 0x875C48: void __cdecl AptDisplayList::removeObject(AptControlRemoveObject2* pRemoveObject2)
    // 0x875CA0: void __cdecl AptDisplayList::removeClonedObject(AptCIH* pObject)
    // 0x875CF8: void __cdecl AptDisplayList::deallocAssetStringRecursive()
    // 0x875D48: AptDisplayListState* __cdecl AptDisplayList::getState()
    // 0x875D50: void __cdecl AptDisplayList::useState(AptDisplayListState* pNewState)
    // 0x875D58: void __cdecl AptDisplayList::RemoveFromDisplayList(AptNativeHash* pHash, AptCIH* pTmp)
    // 0x876170: void __cdecl AptDisplayList::_addToSetCaches(AptCIH* pItem, int bQueueClipEvents)
    // 0x876688: void __cdecl AptDisplayList::render(AptRenderingContext* pRenderingContext, AptMaskRenderOperation eMaskOperation)
    // 0x876868: void __cdecl AptDisplayList::_getBoundingRect(AptRenderingContext* pRenderingContext, AptRect* pRect)
    // 0x876938: void __cdecl AptDisplayList::tick()
    // 0x8769A0: void __cdecl AptDisplayList::clear(bool bClean)
    // 0x876A68: void __cdecl AptDisplayList::PreDestroy()
    // 0x876AE0: void __cdecl AptDisplayList::validate(AptCIH* pParent)
    // 0x876FF8: void __cdecl AptDisplayList::instantiateCharacter(int nTargetDepth, AptCharacter* pCharacter, const EAStringC* pName, AptCIH* pParent, int bForceNewInstance, int nClipDepth, AptCIH** ppCIH, int* pbNeedNewInst)
    // 0x8777D0: AptCIH* __cdecl AptDisplayList::placeObject(AptCIH* pItem, int nTargetDepth, AptCharacter* pCharacter, EAStringC* pName, AptCIH* pParent, int bForceNewInstance, int nClipDepth, AptCXForm* pCXForm, AptMatrix* pMatrix, AptEventActionSet* pActions, float fRatio, AptValue* pInitObject)
    // 0x877AD8: void __cdecl AptDisplayList::~AptDisplayList()
    // 0x877C10: AptCIH* __cdecl AptDisplayList::placeObjectNCXForm(AptCIH* pItem, int nTargetDepth, AptCharacter* pCharacter, EAStringC* pName, AptCIH* pParent, int bForceNewInstance, int nClipDepth, AptnCXForm* pnCXForm, AptMatrix* pMatrix, AptEventActionSet* pActions, float fRatio)
    // 0x877D00: AptCIH* __cdecl AptDisplayList::placeObject(AptControlPlaceObject2* pPlaceObject2, AptCIH* pParent)
    // 0x878118: AptCIH* __cdecl AptDisplayList::placeObject(AptPseudoCIH_t* pNewItem, AptCIH* pParentSprite)
    // 0x878280: void __cdecl AptDisplayList::AptDisplayList()
    // 0x8782D8: AptCIH* __cdecl AptDisplayList::AddToDisplayList(AptNativeHash* pHash, AptPseudoCIH_t* pNewControl, AptCIH* pParentCIH)
    // 0x8783B8: void __cdecl AptDisplayList::ReplaceDisplyListItem(AptNativeHash* pHash, AptCIH* pOriginalItem, AptPseudoCIH_t* pNewItem, AptCIH* pParent)
    // 0x878478: void __cdecl AptDisplayList::mergeState(AptPseudoDisplayList* pNewState, AptNativeHash* pOrigObject, bool bJumpAhead)
};
// static_assert(sizeof(AptDisplayList) == 4);  // 32-bit console layout

// ---- AptScriptFunction2  (sizeof = 52) ----
class AptScriptFunction2 : public AptScriptFunctionBase {
    /* +0x30 */ AptAction_DefineFunction2* mpFunction;
    // --- methods (address @ B4Extern) ---
    // 0x85DC18: virtual void __cdecl AptScriptFunction2::SetupBeforeExecution(_AptScriptFunctionState* pState, AptValue* pContext)
    // 0x85DE68: virtual void __cdecl AptScriptFunction2::CleanupAfterExecution(_AptScriptFunctionState* pState)
    // 0x85DFC8: virtual void __cdecl AptScriptFunction2::~AptScriptFunction2()
    // 0x85E4B0: void __cdecl AptScriptFunction2::AptScriptFunction2(AptScriptFunctionBase* pCreatorFunction, AptAction_DefineFunction2* _pFunction, AptCIH* pCurCIH)
    // 0x85E508: void __cdecl AptScriptFunction2::AptScriptFunction2(AptScriptFunction2* pOrigFunc, AptCIH* pCurCIH)
    // 0x85E658: virtual const char* __cdecl AptScriptFunction2::GetName()
    // 0x85E668: virtual unsigned int __cdecl AptScriptFunction2::GetNumArguments()
    // 0x85E7C8: virtual const unsigned char* __cdecl AptScriptFunction2::GetByteCodeBase()
    // 0x85E7D8: virtual unsigned int __cdecl AptScriptFunction2::GetByteCodeSize()
    // 0x85E7E8: virtual AptConstantPool __cdecl AptScriptFunction2::GetConstantPool()
    // 0x85E808: virtual void __cdecl AptScriptFunction2::SetArgument(AptValue* pValue, int nIndex)
    // 0x85E9C8: virtual AptScriptFunctionBase* __cdecl AptScriptFunction2::Duplicate(AptCIH* pCurCIH)
};
// static_assert(sizeof(AptScriptFunction2) == 52);  // 32-bit console layout

// ---- AptActionInterpreter::FunctionTable  (sizeof = 4) ----
struct AptActionInterpreter::FunctionTable {
    /* +0x00 */ void  (__cdecl * mFunctionPointer)(AptActionInterpreter* const , AptActionInterpreter::LocalContextT* const );
};
// static_assert(sizeof(AptActionInterpreter::FunctionTable) == 4);  // 32-bit console layout

// ---- AptActionInterpreter::LocalContextT  (sizeof = 28) ----
struct AptActionInterpreter::LocalContextT {
    /* +0x00 */ const unsigned char* pInstruction;
    /* +0x04 */ AptCIH* pCurrentContext;
    /* +0x08 */ AptValue* pCurWith;
    /* +0x0c */ unsigned char* pRemoveWithAt;
    /* +0x10 */ AptValue* pSuper;
    /* +0x14 */ bool bEncounteredReturn;
    /* +0x18 */ AptCharacterInst* pParentCharacter;
};
// static_assert(sizeof(AptActionInterpreter::LocalContextT) == 28);  // 32-bit console layout

// ---- AptUserFunctions  (sizeof = 156) ----
struct AptUserFunctions {
    /* +0x00 */ void*  (__cdecl * pfnMemAlloc)(unsigned int);
    /* +0x04 */ void  (__cdecl * pfnMemFree)(void*);
    /* +0x08 */ void  (__cdecl * pfnMemFreeSize)(void*, unsigned int);
    /* +0x0c */ void  (__cdecl * pfnAssertFail)(const char*, const char*, unsigned int);
    /* +0x10 */ void  (__cdecl * pfnSetBackgroundColour)(unsigned int);
    /* +0x14 */ void  (__cdecl * pfnDebugPrint)(const char*, ...);
    /* +0x18 */ void  (__cdecl * pfnDebugAddSavedInput)(AptSavedInputRecord*, int);
    /* +0x1c */ void  (__cdecl * pfnDebugSetScreenGrabPending)(const char*);
    /* +0x20 */ void  (__cdecl * pfnLoadAnimation)(const char*, AptSharedPtr<AptFile>);
    /* +0x24 */ void  (__cdecl * pfnFreeAnimation)(void*);
    /* +0x28 */ void  (__cdecl * pfnFreeConstantTable)(void*);
    /* +0x2c */ void  (__cdecl * pfnLoadAnimationCompleted)(const char*, const char*);
    /* +0x30 */ void  (__cdecl * pfnCommand)(const char*, const char*);
    /* +0x34 */ AptValue*  (__cdecl * pfnLoadVariables)(const char*);
    /* +0x38 */ AptValue*  (__cdecl * pfnLoadVariablesNULL)();
    /* +0x3c */ void  (__cdecl * pfnSetExternVariable)(const char*, const char*);
    /* +0x40 */ AptValue*  (__cdecl * pfnGetExternVariable)(const char*);
    /* +0x44 */ void  (__cdecl * pfnSendVariables)(const char*, const char*, const char*, const char*, int);
    /* +0x48 */ void*  (__cdecl * pfnAllocateString)(AptAllocateStringParameters*);
    /* +0x4c */ void  (__cdecl * pfnDeallocateString)(void*, unsigned int);
    /* +0x50 */ void  (__cdecl * pfnDrawString)(void*, AptMaskRenderOperation);
    /* +0x54 */ void*  (__cdecl * pfnLoadTexture)(void*, int);
    /* +0x58 */ void  (__cdecl * pfnFreeTexture)(void*);
    /* +0x5c */ void  (__cdecl * pfnBindTexture)(void*, int, void*);
    /* +0x60 */ void*  (__cdecl * pfnLoadRenderingUnit)(void*, int);
    /* +0x64 */ void  (__cdecl * pfnFreeRenderingUnit)(void*);
    /* +0x68 */ void  (__cdecl * pfnSetVertexMatrix)(AptMatrix*);
    /* +0x6c */ void  (__cdecl * pfnSetColourTransform)(AptCXForm*);
    /* +0x70 */ void  (__cdecl * pfnDrawRenderingUnit)(void*, AptMaskRenderOperation);
    /* +0x74 */ void  (__cdecl * pfnCustomControlRender)(char*, char*, void*, const char*);
    /* +0x78 */ bool  (__cdecl * pfnCustomControlUpdate)(void*);
    /* +0x7c */ int  (__cdecl * pfnPointHitTest)(float, float, void*);
    /* +0x80 */ void  (__cdecl * pfnGetRealTimeClock)(AptSysClock*, bool);
    /* +0x84 */ int  (__cdecl * pfnGetBytesTotal)(const char*, AptGetBytesEnum);
    /* +0x88 */ int  (__cdecl * pfnGetBytesLoaded)(const char*, AptGetBytesEnum);
    /* +0x8c */ void  (__cdecl * pfnUninitializedVarAccess)(const char*);
    /* +0x90 */ float  (__cdecl * pfnGetStageHeight)();
    /* +0x94 */ float  (__cdecl * pfnGetStageWidth)();
    /* +0x98 */ void  (__cdecl * pfnCustomSavedInputHandler)(void*, unsigned int);
    // --- methods (address @ B4Extern) ---
    // 0x826140: void __cdecl AptUserFunctions::AptUserFunctions()
};
// static_assert(sizeof(AptUserFunctions) == 156);  // 32-bit console layout

// ---- AptSavedInputRecordCustom  (sizeof = 8) ----
struct AptSavedInputRecordCustom : public AptSavedInputRecord {
    /* +0x04 */ unsigned short nInputType;
    /* +0x06 */ unsigned short nInputBufferSize;
};
// static_assert(sizeof(AptSavedInputRecordCustom) == 8);  // 32-bit console layout

// ---- AptSavedInputRecordInput  (sizeof = 8) ----
struct AptSavedInputRecordInput : public AptSavedInputRecord {
    /* +0x04 */ unsigned int nInput;
};
// static_assert(sizeof(AptSavedInputRecordInput) == 8);  // 32-bit console layout

// ---- AptFastStack  (sizeof = 1) ----
class AptFastStack {
    /* +0x00 */ AptValue* mPrev;
    /* +0x04 */ AptValue* mNext;
};
// static_assert(sizeof(AptFastStack) == 1);  // 32-bit console layout

// ---- AptActionInterpreter::_FunctionAptActionPushStringDictWord::__l2::<unnamed-tag>::<unnamed-tag>  (sizeof = 2) ----
struct AptActionInterpreter::_FunctionAptActionPushStringDictWord::__l2::<unnamed-tag>::<unnamed-tag> {
    /* +0x00 */ char c0;
    /* +0x01 */ char c1;
};
// static_assert(sizeof(AptActionInterpreter::_FunctionAptActionPushStringDictWord::__l2::<unnamed-tag>::<unnamed-tag>) == 2);  // 32-bit console layout

// ---- AptActionInterpreter::_FunctionAptActionPushStringDictWord::__l2::<unnamed-tag>  (sizeof = 2) ----
union AptActionInterpreter::_FunctionAptActionPushStringDictWord::__l2::<unnamed-tag> {
    /* +0x00 */ unsigned short uDictionary;
    /* +0x00 */ struct {
        char c0;
        char c1;
    };
};
// static_assert(sizeof(AptActionInterpreter::_FunctionAptActionPushStringDictWord::__l2::<unnamed-tag>) == 2);  // 32-bit console layout

// ---- AptActionInterpreter::_FunctionAptActionPushFloat::__l2::<unnamed-tag>::<unnamed-tag>  (sizeof = 4) ----
struct AptActionInterpreter::_FunctionAptActionPushFloat::__l2::<unnamed-tag>::<unnamed-tag> {
    /* +0x00 */ char c0;
    /* +0x01 */ char c1;
    /* +0x02 */ char c2;
    /* +0x03 */ char c3;
};
// static_assert(sizeof(AptActionInterpreter::_FunctionAptActionPushFloat::__l2::<unnamed-tag>::<unnamed-tag>) == 4);  // 32-bit console layout

// ---- AptActionInterpreter::_FunctionAptActionPushFloat::__l2::<unnamed-tag>  (sizeof = 4) ----
union AptActionInterpreter::_FunctionAptActionPushFloat::__l2::<unnamed-tag> {
    /* +0x00 */ float fValue;
    /* +0x00 */ struct {
        char c0;
        char c1;
        char c2;
        char c3;
    };
};
// static_assert(sizeof(AptActionInterpreter::_FunctionAptActionPushFloat::__l2::<unnamed-tag>) == 4);  // 32-bit console layout

// ---- AptActionInterpreter::_FunctionAptActionPushWord::__l2::<unnamed-tag>::<unnamed-tag>  (sizeof = 2) ----
struct AptActionInterpreter::_FunctionAptActionPushWord::__l2::<unnamed-tag>::<unnamed-tag> {
    /* +0x00 */ unsigned char c0;
    /* +0x01 */ unsigned char c1;
};
// static_assert(sizeof(AptActionInterpreter::_FunctionAptActionPushWord::__l2::<unnamed-tag>::<unnamed-tag>) == 2);  // 32-bit console layout

// ---- AptActionInterpreter::_FunctionAptActionPushWord::__l2::<unnamed-tag>  (sizeof = 2) ----
union AptActionInterpreter::_FunctionAptActionPushWord::__l2::<unnamed-tag> {
    /* +0x00 */ short nValue;
    /* +0x00 */ struct {
        unsigned char c0;
        unsigned char c1;
    };
};
// static_assert(sizeof(AptActionInterpreter::_FunctionAptActionPushWord::__l2::<unnamed-tag>) == 2);  // 32-bit console layout

// ---- AptActionInterpreter::_FunctionAptActionPushDWord::__l2::<unnamed-tag>::<unnamed-tag>  (sizeof = 4) ----
struct AptActionInterpreter::_FunctionAptActionPushDWord::__l2::<unnamed-tag>::<unnamed-tag> {
    /* +0x00 */ unsigned char c0;
    /* +0x01 */ unsigned char c1;
    /* +0x02 */ unsigned char c2;
    /* +0x03 */ unsigned char c3;
};
// static_assert(sizeof(AptActionInterpreter::_FunctionAptActionPushDWord::__l2::<unnamed-tag>::<unnamed-tag>) == 4);  // 32-bit console layout

// ---- AptActionInterpreter::_FunctionAptActionPushDWord::__l2::<unnamed-tag>  (sizeof = 4) ----
union AptActionInterpreter::_FunctionAptActionPushDWord::__l2::<unnamed-tag> {
    /* +0x00 */ int nValue;
    /* +0x00 */ struct {
        unsigned char c0;
        unsigned char c1;
        unsigned char c2;
        unsigned char c3;
    };
};
// static_assert(sizeof(AptActionInterpreter::_FunctionAptActionPushDWord::__l2::<unnamed-tag>) == 4);  // 32-bit console layout

// ---- AptAction_GotoFrame2  (sizeof = 4) ----
struct AptAction_GotoFrame2 {
    /* +0x00 */ int bPlay;
};
// static_assert(sizeof(AptAction_GotoFrame2) == 4);  // 32-bit console layout

// ---- AptAction_PushString  (sizeof = 4) ----
struct AptAction_PushString {
    /* +0x00 */ char* szStringToBePushed;
};
// static_assert(sizeof(AptAction_PushString) == 4);  // 32-bit console layout

// ---- AptAction_With  (sizeof = 4) ----
struct AptAction_With {
    /* +0x00 */ unsigned char* pEnd;
};
// static_assert(sizeof(AptAction_With) == 4);  // 32-bit console layout

// ---- AptAction_GotoFrame  (sizeof = 4) ----
struct AptAction_GotoFrame {
    /* +0x00 */ int nFrame;
};
// static_assert(sizeof(AptAction_GotoFrame) == 4);  // 32-bit console layout

// ---- AptAction_Push  (sizeof = 8) ----
struct AptAction_Push {
    /* +0x00 */ AptConstantPool items;
};
// static_assert(sizeof(AptAction_Push) == 8);  // 32-bit console layout

// ---- AptAction_SetTarget  (sizeof = 4) ----
struct AptAction_SetTarget {
    /* +0x00 */ char* szTarget;
};
// static_assert(sizeof(AptAction_SetTarget) == 4);  // 32-bit console layout

// ---- AptAction_StoreRegister  (sizeof = 4) ----
struct AptAction_StoreRegister {
    /* +0x00 */ int nRegister;
};
// static_assert(sizeof(AptAction_StoreRegister) == 4);  // 32-bit console layout

// ---- AptAction_BranchAddress  (sizeof = 4) ----
struct AptAction_BranchAddress {
    /* +0x00 */ int nTargetDelta;
};
// static_assert(sizeof(AptAction_BranchAddress) == 4);  // 32-bit console layout

// ---- AptAction_GetUrl  (sizeof = 8) ----
struct AptAction_GetUrl {
    /* +0x00 */ char* szUrl;
    /* +0x04 */ char* szWin;
};
// static_assert(sizeof(AptAction_GetUrl) == 8);  // 32-bit console layout

// ---- AptAction_GotoLabel  (sizeof = 4) ----
struct AptAction_GotoLabel {
    /* +0x00 */ char* szLabel;
};
// static_assert(sizeof(AptAction_GotoLabel) == 4);  // 32-bit console layout

// ---- AptRenderingContext  (sizeof = 960) ----
struct AptRenderingContext {
    /* +0x00 */ AptCXForm curCXForm;
    /* +0x20 */ AptMatrix curVertexMatrix;
    /* +0x38 */ AptCXForm aCXFormStack[16];
    /* +0x238 */ AptMatrix aVertexMatrixStack[16];
    /* +0x3b8 */ int nCXFormStack;
    /* +0x3bc */ int nVertexMatrixStack;
    // --- methods (address @ B4Extern) ---
    // 0x87D878: void __cdecl AptRenderingContext::AptRenderingContext()
    // 0x87D8D0: void __cdecl AptRenderingContext::pushColourTransform()
    // 0x87D910: void __cdecl AptRenderingContext::popColourTransform()
    // 0x87D950: void __cdecl AptRenderingContext::appendColourTransform(AptCXForm* pCXForm)
    // 0x87D9E8: void __cdecl AptRenderingContext::getVertexMatrix(AptMatrix* pMatrix)
    // 0x87DA40: void __cdecl AptRenderingContext::pushVertexMatrix()
    // 0x87DA88: void __cdecl AptRenderingContext::popVertexMatrix()
    // 0x87DAE8: virtual void __cdecl AptRenderingContext::multMatrix(AptMatrix* pA, AptMatrix* pB, AptMatrix* pOut) = 0
    // 0x87DBB8: void __cdecl AptRenderingContext::appendVertexMatrix(AptMatrix* pMatrix)
    // 0x87DBF8: void __cdecl AptRenderingContext::expandBoundingRect(AptRect* pBoundingRect, AptRect* pNewRect)
};
// static_assert(sizeof(AptRenderingContext) == 960);  // 32-bit console layout

// ---- AptSavedInputRecordCheckpoint  (sizeof = 260) ----
struct AptSavedInputRecordCheckpoint : public AptSavedInputRecord {
    /* +0x04 */ char szBuf[256];
};
// static_assert(sizeof(AptSavedInputRecordCheckpoint) == 260);  // 32-bit console layout

// ---- AptValueFactory  (sizeof = 1) ----
class AptValueFactory {
    // --- methods (address @ B4Extern) ---
    // 0x85D088: virtual AptValue* __cdecl AptValueFactory::CreateString(const char* szValue) = 0
    // 0x85D090: virtual AptValue* __cdecl AptValueFactory::CreateArray(int nElements, AptValue** pAptValue) = 0
    // 0x85D0F0: virtual AptValue* __cdecl AptValueFactory::CreateStringFormatted(const char* szFormat, ...) = 0
    // 0x85D170: virtual AptValue* __cdecl AptValueFactory::CreateUndefined() = 0
    // 0x85D180: virtual AptValue* __cdecl AptValueFactory::CreateInteger(int nValue) = 0
    // 0x85D2E8: virtual AptValue* __cdecl AptValueFactory::CreateFloat(float fValue) = 0
    // 0x85D450: virtual AptValue* __cdecl AptValueFactory::CreateBoolean(bool bValue) = 0
};
// static_assert(sizeof(AptValueFactory) == 1);  // 32-bit console layout
