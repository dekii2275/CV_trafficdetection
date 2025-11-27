export default function Sidebar() {
    return (
      <div className="w-60 h-screen bg-[#111827] border-r border-gray-700 p-4 flex flex-col gap-6">
        <h1 className="text-lg font-semibold">Traffic AI Dashboard</h1>
  
        <div>
          <h2 className="text-sm text-gray-400 mb-2">Cameras</h2>
          <div className="flex flex-col gap-2">
            <button className="bg-[#1E293B] px-3 py-2 rounded text-left">
              RTSP: Cam 01
            </button>
            <button className="bg-[#1E293B] px-3 py-2 rounded text-left">
              Upload: File.mp4
            </button>
          </div>
        </div>
  
        <div>
          <h2 className="text-sm text-gray-400 mb-2">Config</h2>
          <div className="flex flex-col gap-2">
            <button className="bg-[#1E293B] px-3 py-2 rounded text-left">
              ROI / Count Line
            </button>
            <button className="bg-[#1E293B] px-3 py-2 rounded text-left">
              Model: yolov8n
            </button>
            <button className="bg-[#1E293B] px-3 py-2 rounded text-left">
              Overlay: On
            </button>
          </div>
        </div>
      </div>
    );
  }
  