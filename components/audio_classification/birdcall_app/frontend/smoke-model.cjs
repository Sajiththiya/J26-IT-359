// Run the UI checks with real inference, not demo mode.
process.env.EXPECT_DEMO = "false";
require("./smoke-test.cjs");
