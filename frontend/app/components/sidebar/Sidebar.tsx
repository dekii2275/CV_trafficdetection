import { 
  Cpu, 
  Zap, 
  Layers, 
  Maximize, 
  Eye, 
  Sliders, 
  BoxSelect, 
  HardDrive
} from "lucide-react";

// Sidebar: Thanh điều hướng trái của Dashboard
export default function Sidebar() {
  return (
    <div className="w-64 h-screen bg-[#0f172a] border-r border-slate-800 flex flex-col text-slate-300 font-mono">
      
      {/* Header – Tên hệ thống */}
      <div className="p-5 border-b border-slate-800">
        <h1 className="text-white font-bold text-base tracking-tight flex items-center gap-2">
          <Zap size={20} className="text-yellow-500 fill-yellow-500/20" />
          TRAFFIC AI 
          <span className="text-[10px] bg-slate-800 px-1 py-0.5 rounded text-slate-400">CORE</span>
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        
        {/* Khối cấu hình AI (Model + Device + Precision) */}
        <Section title="AI Engine Profile">
          <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-3">
            <Row label="Model Arch" value="YOLOv8-Nano" valueClass="text-green-400 bg-green-400/10" />
            <Row label="Compute Device" value={<><Cpu size={12}/> CUDA (GPU)</>} valueClass="text-blue-400" />
            <Row label="Precision" value="FP16 (Half)" />
          </div>
        </Section>

        {/* Tham số phát hiện (Confidence, IoU, Classes) */}
        <Section title="Detection Params">
          <div className="space-y-4">
            
            {/* Thanh conf */}
            <SliderItem label="Confidence (Conf)" value="0.40" barColor="bg-blue-500" width="40%" />
            
            {/* Thanh IoU */}
            <SliderItem label="NMS IoU" value="0.50" barColor="bg-purple-500" width="50%" />

            {/* Danh sách class đang bật */}
            <div>
              <div className="text-[10px] uppercase text-slate-500 mb-2">Active Classes</div>
              <div className="flex flex-wrap gap-2">
                <ClassBadge label="Car" color="bg-blue-500/20 text-blue-400 border-blue-500/30" />
                <ClassBadge label="Truck" color="bg-orange-500/20 text-orange-400 border-orange-500/30" />
                <ClassBadge label="Bus" color="bg-yellow-500/20 text-yellow-400 border-yellow-500/30" />
                <ClassBadge label="Motor" color="bg-green-500/20 text-green-400 border-green-500/30" />
              </div>
            </div>

          </div>
        </Section>

        {/* Cấu hình pipeline: độ phân giải, skip, buffer… */}
        <Section title="Pipeline Config">
           <div className="grid grid-cols-2 gap-2">
              <ConfigBox icon={<Maximize size={14}/>} label="Input Res" value="360p" />
              <ConfigBox icon={<Layers size={14}/>} label="Skip Frame" value="5" />
              <ConfigBox icon={<Eye size={14}/>} label="Track Buffer" value="30" />
              <ConfigBox icon={<HardDrive size={14}/>} label="Img Quality" value="30%" />
           </div>
        </Section>

        {/* Trạng thái vùng ROI đang bật */}
        <Section title="Active ROI Zones">
            <div className="space-y-2">
                <RoiStatus label="Cam 01: Cổng Chính" points={4} active />
                <RoiStatus label="Cam 02: Ngã Tư A" points={5} active />
                <RoiStatus label="Cam 03: Ngã Tư B" points={0} active={false} />
            </div>
        </Section>

      </div>
      
      {/* Footer – Thông tin backend */}
      <div className="p-4 border-t border-slate-800 text-[10px] text-slate-600 text-center">
        Backend: v1.0.2 | Multiprocessing: ON
      </div>
    </div>
  );
}

// Nhãn + Giá trị trong phần AI Engine Profile
function Row({ label, value, valueClass="" }: { label: string; value: any; valueClass?: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-xs text-slate-400">{label}</span>
      <span className={`text-xs font-bold px-2 py-0.5 rounded ${valueClass}`}>{value}</span>
    </div>
  );
}

// Thanh slider hiển thị Conf / IoU
function SliderItem({ label, value, barColor, width }: any) {
  return (
    <div>
      <div className="flex justify-between text-[10px] uppercase text-slate-500 mb-1">
        <span>{label}</span>
        <span className="text-white">{value}</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full ${barColor}`} style={{ width }}></div>
      </div>
    </div>
  );
}

// Khung nhóm tiêu đề
function Section({ title, children }: { title: string, children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
        <Sliders size={10} /> {title}
      </h3>
      {children}
    </div>
  );
}

// Badge class (Car / Motor / Truck…)
function ClassBadge({ label, color }: { label: string, color: string }) {
  return (
    <span className={`text-[10px] px-2 py-1 rounded border ${color} font-medium`}>
      {label}
    </span>
  );
}

// Box cấu hình nhỏ (Input Res, Skip Frame…)
function ConfigBox({ icon, label, value }: { icon: any, label: string, value: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 p-2 rounded flex flex-col items-center justify-center gap-1">
      <div className="text-slate-500">{icon}</div>
      <div className="text-[9px] text-slate-400 uppercase">{label}</div>
      <div className="text-xs font-bold text-white">{value}</div>
    </div>
  );
}

// Trạng thái ROI từng cam
function RoiStatus({ label, points, active }: { label: string, points: number, active: boolean }) {
  return (
    <div className={`flex justify-between items-center p-2 rounded border ${
      active ? 'bg-slate-900 border-slate-800' : 'bg-slate-900/30 border-slate-800/30 opacity-50'
    }`}>
      <div className="flex items-center gap-2">
        <BoxSelect size={14} className={active ? "text-green-500" : "text-slate-600"} />
        <span className="text-xs">{label}</span>
      </div>
      <span className="text-[10px] bg-slate-800 px-1.5 rounded text-slate-400">{points} pts</span>
    </div>
  );
}
