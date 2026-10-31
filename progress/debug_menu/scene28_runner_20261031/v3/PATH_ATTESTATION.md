# Exact debug-variable path derivation at B5 3f

All derivation below is from published B5 3f4f9c06e1a694d491effd1cbe28407ce9df1d4b Git blobs, not mutable worktree files. The blob IDs for each implementation file are in SOURCE_PINS.json and SCOPE.json.

## Core path construction

CgsDebugComponent::GetComponentPath (CgsDebugComponent.cpp, ARTIST 0x82822218) formats GetPath + "/" + GetName. The base GetPath returns an empty string. MakeFullPath (ARTIST 0x828222C8) appends a grouped path and uses the original unconditional separator behavior. DebugComponent::RegisterVariable uses GetComponentPath for the ungrouped overload and MakeFullPath for the grouped overload.

VariableManager::RegisterVariable creates the group menu from the supplied path, then attaches the variable leaf name. MenuManager::GetMenuFromPath starts at the root when the parent is null and treats slash and backslash as path delimiters. DebugInterface::RegisterVariable forwards its supplied path directly to VariableManager; it does not add a component prefix.

## Derived paths used by the aliases

| Target family | Source construction | Raw path prefix |
|---|---|---|
| Scene Manager | SceneManagerDebugComponent has no GetPath override and GetName returns Scene manager. It registers the selected leaves without a group. | /Scene manager |
| Director | Director DebugComponent has no GetPath override and GetName returns Camera. Grouped leaves use MakeFullPath; empty-group leaves attach to the Camera page. | /Camera |
| ShadowMap | ShadowMap::Construct calls DebugInterface with literal path World\\ShadowMap and leaf name. This starts at the root variable manager. | /World/ShadowMap |

The complete per-control paths are in SCOPE.json raw_readback_path. The Case setup does not select a World component for ShadowMap; it defines the literal World/ShadowMap aliases at root. It selects Scene manager and Camera only for their component-backed registrations.

## Target prefixes and exact names

Scene Manager aliases bind to /Scene manager/ followed by the exact Source41 leaf caption. Director aliases bind to /Camera/, the exact source group where present, and the leaf; the original Debug Ouput typo is preserved. ShadowMap aliases bind to /World/ShadowMap/ and the exact Source41 leaf caption.

Each raw read uses the bound alias, native value, and bound alias again. Both alias lines must equal alias + colon + the full path above before that row can be accepted.
## Exact source references

- CgsDebugComponent.cpp:83 GetComponentPath; :104 MakeFullPath; :127/161 grouped and ungrouped RegisterVariable overloads. The exact 3f blob is in SOURCE_PINS.json.
- CgsSceneManagerDebugComponent.cpp:81-84 returns the Scene manager name; OnActivate registers the selected leaves in that component.
- BrnDirectorModuleDebugCompononent.cpp:49 returns Camera. Its selected controls are registered in BrnDirectorModuleDebugCompononent_wS34_02.cpp.
- CgsDebugInterface.cpp:107-113 forwards the supplied path and variable leaf to VariableManager.
- CgsVariableManager.cpp:83 registers the menu under the supplied group path and attaches the variable leaf.
- CgsMenuManager.cpp:42 creates the path; :245 parses both slash and backslash separators from the root menu.
- BrnShadowMap.cpp:269-276 passes the literal World\\ShadowMap group to DebugInterface.

This computes each raw path prefix from current3f source: Scene Manager is /Scene manager, Director is /Camera, and ShadowMap is /World/ShadowMap. The driver defines the full literal ShadowMap paths without a World component selector. The source aliases retain the original captions and the Director Debug Ouput spelling.
## Exact source references

- CgsDebugComponent.cpp:83 GetComponentPath; :104 MakeFullPath; :127 and :161 grouped/ungrouped RegisterVariable; :331-332 base GetName/GetPath.
- CgsSceneManagerDebugComponent.cpp:81-84 returns Scene manager and has no GetPath override.
- BrnDirectorModuleDebugCompononent.cpp:49 returns Camera; its class header has no GetPath override. Selected registrations are in BrnDirectorModuleDebugCompononent_wS34_02.cpp.
- CgsDebugInterface.cpp:107-114 forwards the supplied path and leaf to VariableManager.
- CgsVariableManager.cpp:83 creates the supplied group path and attaches the variable leaf.
- CgsMenuManager.cpp:42 creates path nodes; :245 splits both slash and backslash separators starting at the root for a null parent.
- BrnShadowMap.cpp:269-276 passes literal World\\ShadowMap path strings to DebugInterface.

Therefore the exact current3f registered prefixes are Scene Manager /Scene manager, Director /Camera, and ShadowMap /World/ShadowMap. The slash-normalized full target paths are listed per alias in SCOPE.json and CONTROL_MATRIX.md. ShadowMap aliases are bound as full literal paths without selecting a component.
