import { ApiError } from '../types/api';
import { errorCodeHint } from '../constants/errorCodes';

/** 把后端错误码翻成人话；限流与锁冲突给出可操作提示 */
export const toHumanMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    if (error.code === 'PIPELINE_LOCKED') return '这条管道正在跑，去看当前运行';
    if (error.code === 'RUN_QUOTA_EXCEEDED') return '并发运行数已达上限，请等当前运行结束';
    if (error.code === 'RATE_LIMITED') return '请求过于频繁，正在退避重试';
    if (error.code === 'SOURCE_IN_USE') return error.message;
    return error.detail ? `${error.message}：${error.detail}` : error.message;
  }
  if (error instanceof Error) return error.message;
  return '未知错误';
};

export const errorHint = (error: unknown): string =>
  error instanceof ApiError ? errorCodeHint(error.code) : '请稍后重试';
