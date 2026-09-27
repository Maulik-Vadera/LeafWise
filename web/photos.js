// Upload budget: at most 3 x 1 MB JPEGs plus small multipart overhead.
// This stays below Vercel's 4.5 MB request limit and strips embedded metadata.
const MAX_PIXELS=20_000_000;
const MAX_BYTES=1_000_000;
async function decode(file) {
  if ('createImageBitmap' in window) return createImageBitmap(file);
  const url=URL.createObjectURL(file);
  try {const image=new Image();image.src=url;await image.decode();return {width:image.naturalWidth,height:image.naturalHeight,image,close(){}};}
  finally {URL.revokeObjectURL(url);}
}
const toBlob=(canvas,quality)=>new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(new Error('The photo could not be prepared. Try a different JPG.')),'image/jpeg',quality));
export async function preparePhoto(file) {
  let bitmap;
  try {bitmap=await decode(file);} catch {throw new Error('This photo could not be opened. Try a JPG, PNG or WebP image.');}
  try {
    if(bitmap.width*bitmap.height>MAX_PIXELS)throw new Error('Use a photo under 20 megapixels. Export a smaller copy first.');
    if(Math.min(bitmap.width,bitmap.height)<64)throw new Error('This photo is too small. Use a clear, larger image.');
    const canvas=document.createElement('canvas');
    let scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));
    for(let attempt=0;attempt<3;attempt++) {
      canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));
      const context=canvas.getContext('2d');context.fillStyle='#ffffff';context.fillRect(0,0,canvas.width,canvas.height);context.drawImage(bitmap.image||bitmap,0,0,canvas.width,canvas.height);
      for(const quality of [.88,.76,.64]) {const blob=await toBlob(canvas,quality);if(blob.size<=MAX_BYTES)return blob;}
      scale*=.8;
    }
    throw new Error('This photo is still too large to upload. Export a smaller JPG and try again.');
  } finally {bitmap.close();}
}
