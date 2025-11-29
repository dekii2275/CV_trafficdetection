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

export default function Sidebar() {
  return (
    <div className="w-64 h-screen bg-[#0f172a] border-r border-slate-800 flex flex-col text-slate-300 font-mono">
      
      {/* 1. HEADER: TÊN HỆ THỐNG */}
      <div className="p-5 border-b border-slate-800">
        <h1 className="text-white font-bold text-base tracking-tight flex items-center gap-2">
          <Zap size={20} className="text-yellow-500 fill-yellow-500/20" />
          TRAFFIC AI <span className="text-[10px] bg-slate-800 px-1 py-0.5 rounded text-slate-400">CORE</span>
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        
        {/* 2. AI ENGINE PROFILE (Cấu hình Model) */}
        <Section title="AI Engine Profile">
          <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-400">Model Arch</span>
              <span className="text-xs font-bold text-green-400 bg-green-400/10 px-2 py-0.5 rounded">YOLOv8-Nano</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-400">Compute Device</span>
              <span className="text-xs font-bold text-blue-400 flex items-center gap-1">
                <Cpu size={12} /> CUDA (GPU)
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-400">Precision</span>
              <span className="text-xs text-slate-200">FP16 (Half)</span>
            </div>
          </div>
        </Section>

        {/* 3. DETECTION PARAMETERS (Tham số thuật toán) */}
        <Section title="Detection Params">
          <div className="space-y-4">
            {/* Confidence Threshold */}
            <div>
              <div className="flex justify-between text-[10px] uppercase text-slate-500 mb-1">
                <span>Confidence (Conf)</span>
                <span className="text-white">0.40</span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 w-[40%]"></div>
              </div>
            </div>

            {/* IoU Threshold */}
            <div>
              <div className="flex justify-between text-[10px] uppercase text-slate-500 mb-1">
                <span>NMS IoU</span>
                <span className="text-white">0.50</span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-purple-500 w-[50%]"></div>
              </div>
            </div>

             {/* Active Classes */}
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

        {/* 4. PIPELINE PERFORMANCE (Cấu hình tối ưu mà ta vừa làm) */}
        <Section title="Pipeline Config">
           <div className="grid grid-cols-2 gap-2">
              <ConfigBox icon={<Maximize size={14}/>} label="Input Res" value="360p" />
              <ConfigBox icon={<Layers size={14}/>} label="Skip Frame" value="5" />
              <ConfigBox icon={<Eye size={14}/>} label="Track Buffer" value="30" />
              <ConfigBox icon={<HardDrive size={14}/>} label="Img Quality" value="30%" />
           </div>
        </Section>

        {/* 5. ACTIVE REGIONS (Trạng thái ROI) */}
        <Section title="Active ROI Zones">
            <div className="space-y-2">
                <RoiStatus label="Cam 01: Cổng Chính" points={4} active />
                <RoiStatus label="Cam 02: Ngã Tư A" points={5} active />
                <RoiStatus label="Cam 03: Ngã Tư B" points={0} active={false} />
            </div>
        </Section>

      </div>
      
      {/* FOOTER */}
      <div className="p-4 border-t border-slate-800 text-[10px] text-slate-600 text-center">
        Backend: v1.0.2 | Multiprocessing: ON
      </div>
    </div>
  );
}

// --- SUB COMPONENTS ---

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

function ClassBadge({ label, color }: { label: string, color: string }) {
  return (
    <span className={`text-[10px] px-2 py-1 rounded border ${color} font-medium`}>
      {label}
    </span>
  );
}

function ConfigBox({ icon, label, value }: { icon: any, label: string, value: string }) {
    return (
        <div className="bg-slate-900 border border-slate-800 p-2 rounded flex flex-col items-center justify-center gap-1">
            <div className="text-slate-500">{icon}</div>
            <div className="text-[9px] text-slate-400 uppercase">{label}</div>
            <div className="text-xs font-bold text-white">{value}</div>
        </div>
    )
}

function RoiStatus({ label, points, active }: { label: string, points: number, active: boolean }) {
    return (
        <div className={`flex justify-between items-center p-2 rounded border ${active ? 'bg-slate-900 border-slate-800' : 'bg-slate-900/30 border-slate-800/30 opacity-50'}`}>
            <div className="flex items-center gap-2">
                <BoxSelect size={14} className={active ? "text-green-500" : "text-slate-600"} />
                <span className="text-xs">{label}</span>
            </div>
            <span className="text-[10px] bg-slate-800 px-1.5 rounded text-slate-400">{points} pts</span>
        </div>
    )
}