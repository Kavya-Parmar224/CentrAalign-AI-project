import React, { useRef, useEffect } from 'react';
import { Globe, FileText, Link, MessageCircle, Zap, CheckCircle, XCircle } from 'lucide-react';

export default function AgentTrace({ trace, taskId, API_URL }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [trace]);

  const getIcon = (tool) => {
    switch (tool) {
      case 'browser': return <Globe className="w-4 h-4" />;
      case 'read_file':
      case 'write_file': return <FileText className="w-4 h-4" />;
      case 'http_request': return <Link className="w-4 h-4" />;
      case 'ask_human': return <MessageCircle className="w-4 h-4" />;
      default: return <Zap className="w-4 h-4" />;
    }
  };

  const getFilename = (path) => path ? path.split(/[/\\]/).pop() : '';

  return (
    <div className="flex-1 flex flex-col">
      <h2 className="text-xl font-bold mb-6 text-white border-b border-[#2a2d3e] pb-2 sticky top-0 bg-[#0f1117] z-10 pt-2">
        Execution Trace
      </h2>
      
      {trace.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-[#5c677d] italic">
          Waiting for task...
        </div>
      ) : (
        <div className="space-y-4 pb-20">
          {trace.map((step, i) => (
            <div key={step.id || i} className="bg-[#1a1d2e] rounded-xl p-4 border border-[#2a2d3e] shadow-md animate-fade-in flex gap-4">
              <div className="flex flex-col items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-[#22263b] flex items-center justify-center text-xs font-bold text-[#8892a4]">
                  {i + 1}
                </div>
                {step.status === 'done' && <CheckCircle className="w-5 h-5 text-green-500" />}
                {step.status === 'failed' && <XCircle className="w-5 h-5 text-red-500" />}
                {step.status === 'running' && <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="bg-purple-900/30 text-purple-400 p-1.5 rounded flex items-center gap-1 text-xs font-semibold uppercase tracking-wider">
                    {getIcon(step.tool)} {step.tool || 'Processing'}
                  </span>
                </div>
                
                <div className="bg-[#0f1117] rounded-lg p-3 text-sm text-[#8892a4] mb-3 whitespace-pre-wrap font-mono">
                  {step.reasoning || "Executing step..."}
                </div>

                {step.result && (
                  <div className="text-sm text-gray-300 bg-[#22263b] p-3 rounded-lg border border-[#2a2d3e]">
                    {step.result}
                  </div>
                )}

                {step.screenshot && (
                  <div className="mt-3">
                    <img 
                      src={`${API_URL}/api/screenshot/${taskId}/${getFilename(step.screenshot)}`} 
                      alt="Step screenshot" 
                      className="h-24 object-cover rounded border border-[#2a2d3e] hover:opacity-80 cursor-pointer transition-opacity"
                      onClick={() => window.open(`${API_URL}/api/screenshot/${taskId}/${getFilename(step.screenshot)}`, '_blank')}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
      )}
    </div>
  );
}
