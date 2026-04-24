import { useState } from "react";
import ChatWindow from "./components/ChatWindow";
import Welcome from "./components/Welcome";

export default function App() {
  const [started, setStarted] = useState(false);
  const [initialQ, setInitialQ] = useState("");

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {!started ? (
        <Welcome onSelect={(q) => { setInitialQ(q); setStarted(true); }} />
      ) : (
        <ChatWindow initialQuestion={initialQ} />
      )}
    </div>
  );
}
