#pragma once

#include "types.hpp"

// CgsDev::DebugUI::Function - a registered debug callback (function pointer + user parameter +
// display name), the unit the debug menu invokes for "action" menu items. Recovered from the
// DecFIGS DWARF (Development/DebugSystem/Core/UI/Functions/CgsFunction.h). DebugCallbackFunction
// is the void(void*) callback type the DebugComponent Register/Unregister-Function API takes.

namespace CgsDev
{
    namespace DebugUI
    {
        struct Function
        {
            friend struct FunctionManager;
            typedef void (*DebugCallbackFunction)(void* lpParameter);

            bool                  Prepare(DebugCallbackFunction lpfFunction, void* lpParameter, const char* lpcName);
            void                  Release();
            DebugCallbackFunction GetFunction();
            void*                 GetParameter();
            const char*           GetName() const;
            void                  Select();

        private:
            DebugCallbackFunction mpFunction;
            void*                 mpParameter;
            const char*           mpcName;
        };
    }
}
