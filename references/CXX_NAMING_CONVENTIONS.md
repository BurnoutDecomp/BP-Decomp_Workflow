# C++ Naming Conventions

This convention is derived from a scan of the project-owned C/C++ code in
`GameSource`, `GameShared`, and `SharedClasses`. Vendored SDK, platform, and
middleware headers should not drive naming choices for new project code.

Use these rules as a portable style for other C++ projects. Replace the example
project prefixes such as `Brn` and `Cgs` with prefixes that fit the target
project.

## Core Style

Names are descriptive, domain-oriented, and mostly PascalCase. Variables use a
compact scope and type prefix system.

| Kind | Style | Examples |
| --- | --- | --- |
| Namespace | PascalCase | `BrnTraffic`, `CgsResource`, `CgsContainers` |
| Class/struct | PascalCase | `Vehicle`, `ResourceManager`, `DebugManager` |
| Interface class | `I` + PascalCase | `IUnresolvedHandler` |
| Function/method | PascalCase verb phrase | `Construct`, `Prepare`, `UpdateMatrix`, `GetSpeed` |
| Enum type | PascalCase, often `E` prefixed | `EActiveRaceCarIndex`, `EHostStatus`, `Flags` |
| Enumerator | `E_` + upper snake case | `E_FLAG_ALIVE`, `E_HOST_STATUS_IDLE` |
| Variable | scope/type prefix + PascalCase | `mpBoostStrategy`, `lfTimeStep`, `muNumBundles` |
| Constant | `K` + type prefix + upper snake case | `KI_MAX_NUM_ENTITIES`, `KU_INVALID`, `KF_GRAVITY` |
| File | Module/project prefix + PascalCase | `BrnTrafficVehicle.h`, `CgsResourceManager.h` |

## Namespaces And Modules

Use PascalCase namespaces for owned code. A namespace should identify a module,
subsystem, or shared library boundary:

```cpp
namespace BrnTraffic
{
class Vehicle;
}

namespace CgsResource
{
class ResourceManager;
}
```

Short lowercase namespaces are acceptable only when matching third-party APIs or
legacy generated APIs. Do not introduce lowercase namespaces for new owned
modules unless the whole project already uses them for that layer.

Project or library prefixes belong at ownership boundaries. For example, a
root-level class or file may use `Brn` or `Cgs`, while a class already inside
`namespace BrnTraffic` can simply be `Vehicle`, `Section`, or `Hull`.

## Files

Name hand-written headers and source files after their primary type or module:

```text
BrnTrafficVehicle.h
BrnBoostManager.cpp
CgsResourceManager.h
VehiclePhysics.h
Wheel.h
```

For cross-project reuse, choose one short project or library prefix for broad
shared code, and omit it only when the directory and namespace already provide
enough ownership context.

Generated files may follow generator or schema names, including lowercase names.
Do not copy generated naming into hand-written code.

Host implementations belong under `src/pc/<subsystem>/` or an established
subsystem `PC` directory. Name support files after their module or primary type
(for example `WindowPresentation.h` and `WorldGeometry.cpp`); do not append
`PCLeaf`. Add directories for useful subsystem boundaries, such as
`pc/gcm/renderengine/reflections` and `pc/debug`. Future target implementations
can follow the same `src/<platform>/<subsystem>/` convention and must be selected
explicitly by that target's build.

Directories do not create C++ namespaces. Give new support types ordinary names
inside their owning namespace; preserve recovered class and method identities.
Keep `// FLAG PC-platform leaf: <reason>` comments and their evidence: this marker
identifies provenance for the faithfulness checker independently of filenames.
An original reference-attributed filename (such as `CgsHardwareInitPS3.cpp`) is
provenance, not proof that the current implementation supports that platform.

## Types

Use PascalCase for classes, structs, typedefs, aliases, and template parameters:

```cpp
class BoostManager;
class ResourceTypePair;
typedef CgsContainers::Array<float32_t, KI_MAX_LANDMARKS_IN_MODE> WaypointDistanceArray;

template< class Type, uint32_t Capacity >
class Array;
```

Use nested classes for implementation details tightly owned by a containing
type:

```cpp
class VehiclePhysics
{
public:
    class AboveGroundTestResult;
private:
    class DriftFlags;
};
```

Interface-like classes use an `I` prefix. Callback typedefs use PascalCase,
usually with a callback suffix, such as `FPerfMonCpuDisplayCallback`.

## Functions

Use PascalCase verb phrases. Prefer clear lifecycle, query, and command verbs:

```cpp
void Construct();
void Destruct();
bool Prepare();
void Release();
void Update(float32_t lfTimeStep);
void RenderHUD();
float32_t GetSpeed() const;
void SetBoostAmount(float32_t lfBoostAmount);
bool IsBoosting() const;
bool HasRoute() const;
void OnTakedown();
```

Common verb families:

| Purpose | Prefixes |
| --- | --- |
| Lifecycle | `Construct`, `Destruct`, `Prepare`, `Release`, `Reset`, `Clear` |
| Accessors | `Get`, `Set` |
| Boolean queries | `Is`, `Has`, `Are`, `Can`, `Do`, `Allow` |
| Per-frame or staged work | `Update`, `Render`, `Process`, `Apply`, `Calc` |
| Events | `On` |
| Debug-only access | `DEBUG_` prefix |
| Private variants | `_Internal`, `_Fast` suffixes |

Do not use lower camel case for new owned functions unless implementing or
overriding an external API that requires it.

## Variables

Variable names are built as:

```text
<scope-prefix><type-prefix><PascalCaseName>
```

The scope prefix is always first:

| Prefix | Scope | Examples |
| --- | --- | --- |
| `m` | Member data | `mEngine`, `mfSpeedMPH`, `mpAttribs` |
| `l` | Local variable or parameter | `lfTimeStep`, `lpVehicle`, `luIndex` |
| `g` | Global variable | `gpDebugPrint`, `gxMessageFilterFlags` |

After the scope prefix, add one or more type/category prefixes:

| Type prefix | Meaning | Examples |
| --- | --- | --- |
| none | Object/value type where scalar prefix is not useful | `mEngine`, `lTransform` |
| `p` | Pointer | `mpBoostStrategy`, `lpBundle` |
| `pp` | Pointer to pointer | `lppMemory`, `lppHull` |
| `a` | Array or fixed collection | `maWheels`, `laMoments` |
| `pa` | Pointer to an array or contiguous buffer | `mpaSections`, `mpaRungs` |
| `ap` | Array of pointers | `mapInterested`, `mapParticles` |
| `pap` | Pointer to an array of pointers | `mpapHulls`, `mpapTextures` |
| `b` | Boolean | `mbCrashing`, `lbIsOnline` |
| `i` | Signed integer | `miIndex`, `liEventId` |
| `u` | Unsigned integer | `muNumBundles`, `luVehicleType` |
| `i8`, `i16`, `i32` | Explicit-width signed integer | `mi8Gear`, `li16Timeout` |
| `u8`, `u16`, `u32` | Explicit-width unsigned integer | `mu8CurrentGear`, `lu16CurrentFrame` |
| `f` | Floating point | `mfTimeStep`, `lfSpeed` |
| `e` | Enum value | `meState`, `leWheel` |
| `x` | Flags, bitfields, masks, packed status | `mxFlags`, `lxEffectFlags` |
| `c` | Character | uncommon alone |
| `pc` | C string pointer, usually `const char*` | `lpcName`, `gpcMessageBuffer` |
| `ac` | Character array | `macName`, `gacDebugPrintStringBuffer` |
| `r` | Reference or domain-specific real value where established | `lrSerialiser`, `mrPitchLimit` |

Combine prefixes from left to right:

```cpp
float32_t mfTimeInState;             // member float
uint32_t muCurrentRival;             // member unsigned integer
bool mbIsReversed;                   // member bool
BoostStrategy* mpBoostStrategy;      // member pointer
Wheel maWheels[eNumDrivenWheels];    // member array
Section* mpaSections;                // member pointer to array/buffer
Hull** mpapHulls;                    // member pointer to array of pointers
char macPlayerName[KI_NAME_LENGTH];  // member array of char

float32_t lfTimeStep;                // local/parameter float
uint32_t luSegment;                  // local/parameter unsigned integer
const Vehicle* lpVehicle;            // local/parameter pointer
const float32_t* lpafWheelRadii;     // local/parameter pointer to float array
```

Use the same prefix rules for function parameters and locals. This is different
from many modern C++ styles, but it is the dominant pattern in this codebase.

## Constants

Prefer typed constants over macros. The dominant public/shared constant form is:

```text
K<TypeCode>_<UPPER_SNAKE_NAME>
```

Common type codes:

| Prefix | Meaning | Examples |
| --- | --- | --- |
| `KI_` | Integer or signed count/index | `KI_MAX_NUM_ENTITIES`, `KI_NAME_LENGTH` |
| `KU_` | Unsigned integer | `KU_INVALID`, `KU_MAX_ACTIVE_BODIES` |
| `KF_` | Float | `KF_GRAVITY`, `KF_MPH_TO_MPS` |
| `KR_` | Real/ratio/radian conversion | `KR_RADS_TO_RPM` |
| `KX_` | Flags, bit masks, status bits | `KX_SECTION_FLAGS_IS_SHORTCUT` |
| `KC_` | Character | use for scalar char constants |
| `KPC_` | Pointer to constant C string | `KPC_DEFAULTCOMPONENTPATH` |
| `KAC_` | Constant character array | use for fixed string buffers |
| `KA*` | Constant arrays, with element type after `A` | `KAI_ACTION_CODE_MAPPING`, `KAPC_ACTION_NAMES` |

For new shared constants, prefer the upper snake case form:

```cpp
static const int32_t KI_MAX_PLAYERS = 8;
static const uint32_t KU_INVALID_INDEX = 0xffffffff;
static const float32_t KF_DEFAULT_SPEED = 30.0f;
static const uint8_t KX_FLAG_VISIBLE = 0x01;
```

Small private constants sometimes use lower `k` plus the same type hint, such as
`kfDefaultBlendFactor`, `ku8ReverseGear`, or `knMaxNumContacts`. Use this only
for very local implementation details, and keep it consistent within the file or
class. Do not mix upper `K` and lower `k` for the same constant family.

## Enums

Enum type names are PascalCase. Use an `E` prefix when the enum represents a
standalone domain type:

```cpp
enum EHostStatus
{
    E_HOST_STATUS_IDLE,
    E_HOST_STATUS_IN_GAME_ROOM,
    E_HOST_STATUS_COUNT
};
```

Nested implementation enums may use short names such as `Flags`, `State`, or
`Type` when the containing class gives enough context:

```cpp
class Vehicle
{
public:
    enum Flags
    {
        E_FLAG_ALIVE = 0x01,
        E_FLAG_COLLIDABLE = 0x04
    };
};
```

Enumerator rules:

1. Use `E_` + upper snake case for new hand-written code.
2. Include the enum subject when values may be used outside a narrow scope:
   `E_HOST_STATUS_IDLE`, `E_ACTIVE_RACE_CAR_INDEX_INVALID`.
3. Use `E_*_COUNT` for count sentinels and `E_*_INVALID` for invalid values.
4. For bit flags, include `FLAG` or `FLAGS` in the enumerator name.
5. Do not mix `E_` upper snake case with `eCamelCase` in the same enum. The
   `eCamelCase` form exists in some legacy/engine-facing code, but `E_` upper
   snake case is the project-owned default.

Generated enum values may be PascalCase when they mirror data schemas. Treat
that as generator output, not the default hand-written convention.

## Globals And Statics

Avoid mutable globals where possible. When globals are needed, use the `g` scope
prefix plus the normal type prefix:

```cpp
extern CgsDev::StrStreamBase* gpDebugPrint;
extern FilterFlag gxMessageFilterFlags;
extern char gacDebugPrintStringBuffer[KI_DEBUGMAXVARGSSTRINGLENGTH];
```

Distinguish file-wide globals from project/module-wide globals by linkage:

| Scope | Linkage | Naming | Examples |
| --- | --- | --- | --- |
| File-wide implementation value | Internal linkage, usually `static` or an unnamed namespace | Usually constant naming, `K...` or private/local `k...` | `KU_NUM_SHADOW_MAPS`, `KF_GRAVITY`, `kfDefaultBlendFactor` |
| Project/module-wide shared variable | External linkage, declared `extern` in an owning header/namespace | `g` scope prefix plus type prefix | `gacDebugPrintStringBuffer`, `gpDebugPrint`, `gxMessageFilterFlags` |
| Class-owned static state | Static data member of a class | Member-style name or established local static-member style | `mpInstance`, `mMutex`, `sSettings` |

File-private constants should not use the `g` prefix just because they are at
file scope. Reserve `g` for variables intentionally shared across translation
units. Put externally visible globals in an owning namespace, declare them in the
module header, and define them in one source file.

Static data members still use member naming when they represent state owned by a
class:

```cpp
static DebugManager* mpInstance;
static rw::core::debug::detail::DebugCriticalSection mMutex;
```

## Acronyms

Keep established domain acronyms uppercase when they are part of a PascalCase
name:

```cpp
GetSpeedMPH()
ICEMoviePlayer
CgsResourceID
BrnTrafficPvs
PS3
IO
AI
```

Be consistent inside one subsystem. If a subsystem has standardized `ID`, do not
introduce `Id` in new adjacent code.

## Macros

Macros are rare in owned code and should be reserved for compile-time switches,
platform integration, or unavoidable preprocessor work. Use upper snake case for
new macros:

```cpp
#define PROJECT_ENABLE_NETWORK_DEBUG 1
```

Prefer `static const`, `enum`, or typed C++ facilities when a macro is not
required.

## Exceptions

The following patterns appear in the scanned code but should not be used as the
default for new projects:

1. Generated AttribSys classes and enum values use schema-driven lowercase or
   PascalCase names such as `physicsvehiclebaseattribs` and `CarStateCount`.
2. Third-party namespaces and types such as `rw`, RenderWare, SDK, and platform
   headers follow their own conventions.
3. Size-check helper types such as `Class_Vehicle_IsTheWrongSize` are legacy
   compile-time assertions. Prefer a modern `static_assert` name or expression
   in new code.
4. Lowercase private constants are acceptable only when the surrounding file or
   class already uses that local style.

## Quick Checklist

Before adding a name, check:

1. Is the owned type, namespace, function, or file PascalCase?
2. Does each variable start with `m`, `l`, or `g` as appropriate?
3. Does each scalar/pointer/array variable carry the right type prefix?
4. Are shared constants `K<TypeCode>_UPPER_SNAKE_CASE`?
5. Are enum values `E_` upper snake case with `COUNT` or `INVALID` sentinels
   where needed?
6. Are generated, external, and platform naming styles isolated from
   hand-written project code?
