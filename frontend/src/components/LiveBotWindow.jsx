import { useEffect, useState } from "react";

export default function LiveBotWindow() {
  const [ts, setTs] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => {
      setTs(Date.now());
    }, 400); // refresh rate
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      style={{
        width: "100%",
        border: "1px solid #222",
        borderRadius: "10px",
        background: "#000",
        overflow: "hidden",
        marginBottom: "16px"
      }}
    >
      <img
        src={`/live?ts=${ts}`}
        style={{
          width: "100%",
          display: "block",
          objectFit: "cover"
        }}
        alt="Bot Live View"
      />
    </div>
  );
}
