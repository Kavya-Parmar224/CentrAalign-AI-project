import React from 'react';
import { FileCheck } from 'lucide-react';

export default function SummaryPanel({ summary, screenshots, taskId, API_URL, onReset }) {
  const getFilename = (path) => path ? path.split(/[/\\]/).pop() : '';

  return (
    <div className="bg-[#1a1d2e] rounded-xl p-5 shadow-lg border border-[#2a2d3e]">
      <div className="flex items-center gap-2 mb-4 text-white border-b border-[#2a2d3e] pb-3">
        <FileCheck className="w-5 h-5 text-purple-400" />
        <h2 className="text-lg font-semibold">Task Complete</h2>
      </div>
      
      <div className="text-sm text-gray-300 mb-6 bg-[#0f1117] p-4 rounded-lg border border-[#2a2d3e] whitespace-pre-wrap">
        {summary}
      </div>

      {screenshots && screenshots.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xs font-semibold text-[#8892a4] uppercase tracking-wider mb-3">Captured Screenshots</h3>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
            {screenshots.map((shot, i) => (
              <a 
                key={i} 
                href={`${API_URL}/api/screenshot/${taskId}/${getFilename(shot)}`} 
                target="_blank" 
                rel="noreferrer"
                className="block group relative aspect-video rounded overflow-hidden border border-[#2a2d3e]"
              >
                <img 
                  src={`${API_URL}/api/screenshot/${taskId}/${getFilename(shot)}`} 
                  alt={`Screenshot ${i+1}`}
                  className="w-full h-full object-cover transition-transform group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center">
                  <span className="opacity-0 group-hover:opacity-100 text-white text-xs font-medium">View Full</span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={onReset}
        className="w-full py-2 bg-[#22263b] hover:bg-[#2c3149] text-white rounded-lg font-medium transition-colors border border-[#2a2d3e]"
      >
        Start New Task
      </button>
    </div>
  );
}
