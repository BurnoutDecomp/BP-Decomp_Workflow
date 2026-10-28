#include "GameShared/GameClasses/Development/DebugSystem/Core/UI/Functions/CgsFunction.h"

// CgsDev::DebugUI::Function method bodies. The stored form of a registered debug action: a callback
// + its user parameter + a display name. Prepare's member set matches the X360
// FunctionManager::RegisterFunction direct fill (0x8282E7E0: *fn = callback; [1] = parameter;
// [2] = name); Select fires the callback; the accessors return the members.

namespace CgsDev
{
    namespace DebugUI
    {
        bool Function::Prepare(DebugCallbackFunction lpfFunction, void* lpParameter, const char* lpcName)
        {
            mpFunction  = lpfFunction;
            mpParameter = lpParameter;
            mpcName     = lpcName;
            return true;
        }

        void Function::Release()
        {
            mpFunction  = nullptr;
            mpParameter = nullptr;
            mpcName     = nullptr;
        }

        Function::DebugCallbackFunction Function::GetFunction() { return mpFunction; }
        void*                           Function::GetParameter(){ return mpParameter; }
        const char*                     Function::GetName() const { return mpcName; }

        void Function::Select()
        {
            if (mpFunction)
                mpFunction(mpParameter);
        }
    }
}
