// fullauto - ReXGlue recompiled project for Full Auto (Xbox 360)

#include <rex/app/title_app.h>

#include "generated/default/fullauto_init.h"

class FullAutoApp : public rex::app::TitleApp {
 public:
  FullAutoApp() : TitleApp("fullauto", kPPCImageConfig) {}
};

REX_TITLE_APP(FullAutoApp)
