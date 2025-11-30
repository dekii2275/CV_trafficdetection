import ChatInterface from "@/modules/features/chat/components/ChatInterface";
import { useMultipleTrafficInfo } from "../hooks/useWebSocket";
import { useEffect, useState } from "react";
import { endpoints } from "@/config";

export default function ChatPage() {
  const [allowedRoads, setAllowedRoads] = useState<string[]>([]);

  useEffect(() => {
    const fetchRoads = async () => {
      try {
        // roads_name endpoint không cần authentication
        const res = await fetch(endpoints.roadNames);
        if (!res.ok) {
          setAllowedRoads([]);
          return;
        }
        const json = await res.json();
        const names: string[] = json?.road_names ?? [];
        setAllowedRoads(names);
      } catch {
        setAllowedRoads([]);
      }
    };
    fetchRoads();
  }, []);

  const { trafficData } = useMultipleTrafficInfo(allowedRoads);
  return (
    <div className="min-h-screen px-2 sm:px-4 py-4 sm:py-6">
      <div className="max-w-7xl mx-auto">
        <ChatInterface trafficData={trafficData} />
      </div>
    </div>
  );
}
