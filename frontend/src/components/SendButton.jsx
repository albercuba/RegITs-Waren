import { Send } from "lucide-react";

export default function SendButton({ disabled, sending, onClick }) {
  return (
    <div className="sticky-send">
      <button className="send-button" disabled={disabled || sending} onClick={onClick} type="button">
        <Send size={22} />
        <span>{sending ? "Sende..." : "E-Mail senden"}</span>
      </button>
    </div>
  );
}