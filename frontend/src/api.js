export async function get(path) {
  const response = await fetch(`/api/${path}`, {signal: AbortSignal.timeout(20000)});
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}

export async function post(path, data) {
  const response = await fetch(`/api/${path}`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data),
    signal:AbortSignal.timeout(260000),
  });
  const result = await response.json();
  if (!response.ok) {
    const error=new Error(typeof result.detail==='string'?result.detail:`Request failed (${response.status})`);
    error.status=response.status;
    throw error;
  }
  return result;
}

export async function patch(path, data) {
  const response=await fetch(`/api/${path}`,{
    method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),
    signal:AbortSignal.timeout(20000),
  });
  const result=await response.json();
  if(!response.ok) throw new Error(typeof result.detail==='string'?result.detail:`Request failed (${response.status})`);
  return result;
}
