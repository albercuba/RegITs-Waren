import { Send } from "lucide-react";

export default function SendButton({ disabled, sending, onClick }) {
  return (
    <div className="sticky-send">
      <button className="send-button" disabled={disabled || sending} onClick={onClick} type="button">
        <Send size={22} />
        <span>{sending ? "Sending..." : "Send Email"}</span>
      </button>
    </div>
  );
}
