// Plain single-thread NAM Core adapter inspired by TONE3000's MIT C-API wrapper.
// Raw targets: no loudness normalization, no extra DC blocker, no fast tanh,
// explicit receptive-field zero-input history. Separate instances own state. Original upstream is unchanged.
#include <cmath>
#include <memory>
#include <string>
#include <vector>
#include <emscripten/emscripten.h>
#include <NAM/activations.h>
#include <NAM/dsp.h>
#include <NAM/get_dsp.h>
namespace {
struct Instance {std::unique_ptr<nam::DSP> model;std::vector<float> buffer;int rate;};
std::vector<std::unique_ptr<Instance>> slots;
std::string error;
Instance* get(int id){return id>0&&size_t(id)<=slots.size()?slots[id-1].get():nullptr;}
}
extern "C" {
EMSCRIPTEN_KEEPALIVE int tb_create(int rate,int maximum){
 if((rate!=44100&&rate!=48000)||maximum<1||maximum>16384)return 0;
 nam::activations::Activation::disable_fast_tanh();
 auto p=std::make_unique<Instance>();p->rate=rate;p->buffer.resize(maximum);
 for(size_t i=0;i<slots.size();++i)if(!slots[i]){slots[i]=std::move(p);return i+1;}
 slots.push_back(std::move(p));return slots.size();
}
EMSCRIPTEN_KEEPALIVE void tb_destroy(int id){if(get(id))slots[id-1].reset();}
EMSCRIPTEN_KEEPALIVE int tb_load(int id,const char* text){
 auto* p=get(id);if(!p){error="Invalid instance";return 0;}
 try{
  auto j=nlohmann::json::parse(text);
  if(j.at("architecture")!="WaveNet"||int(j.at("sample_rate"))!=p->rate){error="Explicit mono WaveNet and matching declared rate required";return 0;}
  nam::ScopedPrewarmOnResetDefault context(false);
  auto model=nam::get_dsp(j,nam::DspLoadOptions{false});
  if(!model||model->NumInputChannels()!=1||model->NumOutputChannels()!=1){error="Only mono input/output supported";return 0;}
  model->SetPrewarmOnReset(false);model->Reset(p->rate,int(p->buffer.size()));
  // Match render_nam.py's rf-1 raw-zero prehistory. Hidden-state zeros alone
  // omit the bias responses propagated through preceding layers.
  int remaining=model->GetPrewarmSamples()-1;
  if(remaining<0||remaining>1000000){error="Invalid receptive field";return 0;}
  while(remaining>0){const int n=std::min(remaining,int(p->buffer.size()));std::fill(p->buffer.begin(),p->buffer.end(),0.f);float* a=p->buffer.data();model->process(&a,&a,n);remaining-=n;}
  p->model=std::move(model);return 1;
 }catch(const std::exception& e){error=e.what();return 0;}
}
EMSCRIPTEN_KEEPALIVE float* tb_buffer(int id){auto* p=get(id);return p?p->buffer.data():nullptr;}
EMSCRIPTEN_KEEPALIVE int tb_process(int id,int frames){
 auto* p=get(id);if(!p||!p->model||frames<0||size_t(frames)>p->buffer.size())return 0;
 float* audio=p->buffer.data();NAM_SAMPLE* input=audio;NAM_SAMPLE* output=audio;p->model->process(&input,&output,frames);return 1;
}
EMSCRIPTEN_KEEPALIVE const char* tb_error(){return error.c_str();}
}

extern "C" EMSCRIPTEN_KEEPALIVE int tb_receptive(int id){auto* p=get(id);return p&&p->model?p->model->GetPrewarmSamples():0;}
