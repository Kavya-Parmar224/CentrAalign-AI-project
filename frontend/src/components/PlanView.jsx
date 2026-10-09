import React from 'react';
import { CheckCircle, Circle, PlayCircle } from 'lucide-react';

export default function PlanView({ plan, currentTrace, status }) {
  if (!plan || !plan.steps) return null;

  // Simplistic progress logic based on trace steps
  const currentStepIndex = currentTrace.length > 0 ? currentTrace.length - 1 : -1;
  const isTaskFinished = status === 'done' || status === 'failed';

  return (
    <div className="bg-[#1a1d2e] rounded-xl p-5 shadow-lg border border-[#2a2d3e]">
      <h2 className="text-lg font-semibold mb-4 text-white">Execution Plan</h2>
      
      <div className="space-y-3">
        {plan.steps.map((step, idx) => {
          let isDone = false;
          let isRunning = false;

          if (isTaskFinished) {
            isDone = status === 'done'; // If overall task is done, mark all steps done
          } else {
            isDone = idx < currentStepIndex || (idx === currentStepIndex && currentTrace[idx]?.status === 'done');
            isRunning = idx === currentStepIndex && currentTrace[idx]?.status !== 'done';
          }

          return (
            <div key={idx} className={`flex items-start gap-3 p-2 rounded-lg transition-colors ${isRunning ? 'bg-[#22263b] border border-[#2a2d3e]' : ''}`}>
              <div className="mt-0.5">
                {isDone ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : isRunning ? (
                  <PlayCircle className="w-5 h-5 text-blue-400 animate-pulse" />
                ) : (
                  <Circle className="w-5 h-5 text-[#444a60]" />
                )}
              </div>
              <div className="flex-1">
                <p className={`text-sm ${isDone ? 'text-[#8892a4] line-through' : isRunning ? 'text-white' : 'text-[#8892a4]'}`}>
                  {step.description || step}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {plan.verification_criteria && (
        <div className="mt-4 pt-4 border-t border-[#2a2d3e]">
          <h3 className="text-xs font-semibold text-[#8892a4] uppercase tracking-wider mb-2">Verification Criteria</h3>
          <p className="text-sm text-gray-300 bg-[#0f1117] p-3 rounded-lg border border-[#2a2d3e]">
            {plan.verification_criteria}
          </p>
        </div>
      )}
    </div>
  );
}
