import type { VehicleType } from "../../lib/types";

interface TableRowProps {
    camera: string;
    vehicles: number;
    dominantType: VehicleType;
}

export default function TableRow({ camera, vehicles, dominantType }: TableRowProps) {
    return (
        <tr>
            <td className="py-2">{camera}</td>
            <td className="py-2">{vehicles}</td>
            <td className="py-2">
                <span className="rounded-full bg-slate-800 px-2 py-1 text-xs capitalize">{dominantType}</span>
            </td>
        </tr>
    );
}
