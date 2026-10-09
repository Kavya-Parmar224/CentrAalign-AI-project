import React from 'react';
import { ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';

export default function VerificationResult({ result }) {
  if (!result) return null;

  const { status, explanation, evidence } = result;

  const styles = {
    VERIFIED: {
      bg: 'bg-green-900/20',
      border: 'border-green-500/30',
      text: 'text-green-400',
      icon: <ShieldCheck className="w-6 h-6 text-green-400" />
    },
    PARTIAL: {
      bg: 'bg-yellow-900/20',
      border: 'border-yellow-500/30',
      text: 'text-yellow-400',
      icon: <ShieldAlert className="w-6 h-6 text-yellow-400" />
    },
    FAILED: {
      bg: 'bg-red-900/20',
      border: 'border-red-500/30',
      text: 'text-red-400',
      icon: <ShieldX className="w-6 h-6 text-red-400" />
    }
  };

  const style = styles[status?.toUpperCase()] || styles.FAILED;

  return (
    <div className={`${style.bg} ${style.border} border rounded-xl p-5 shadow-lg`}>
      <div className="flex items-center gap-3 mb-3">
        {style.icon}
        <h2 className={`text-lg font-bold ${style.text}`}>Verification: {status}</h2>
      </div>
      
      <p className="text-gray-300 text-sm mb-4">
        {explanation}
      </p>
      
      {evidence && evidence.length > 0 && (
        <div className="bg-black/20 rounded-lg p-3">
          <h3 className="text-xs font-semibold text-[#8892a4] uppercase mb-2">Evidence</h3>
          <ul className="list-disc pl-4 space-y-1">
            {evidence.map((item, i) => (
              <li key={i} className="text-sm text-gray-400">{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
