import { spawn } from "node:child_process";
const args = process.argv.slice(2);
const i = args.indexOf("--port");
const port = i >= 0 ? args[i + 1] : process.env.PORT || "3000";
if (!/^\d+$/.test(port)) throw new Error("Invalid port");
const child = spawn(
  process.execPath,
  [
    "node_modules/next/dist/bin/next",
    "dev",
    "--hostname",
    "127.0.0.1",
    "--port",
    port,
  ],
  { stdio: "inherit" },
);
for (const sig of ["SIGTERM", "SIGINT"]) process.on(sig, () => child.kill(sig));
child.on("exit", (code) => process.exit(code || 0));
