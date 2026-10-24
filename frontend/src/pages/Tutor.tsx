import TutorChat from "../components/TutorChat";
import { PageHeader } from "../components/ui";

export default function Tutor() {
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="AI ustoz" subtitle="Claude, ChatGPT, Gemini, kod yozish va avtomatlashtirish bo'yicha istalgan savol" />
      <TutorChat
        suggestions={[
          "Claude va ChatGPT farqi nimada?",
          "MCP nima va menga nima beradi?",
          "Claude Code'ni qanday o'rnataman?",
          "Kundalik ishimni AI bilan qanday avtomatlashtiraman?",
        ]}
      />
    </div>
  );
}
