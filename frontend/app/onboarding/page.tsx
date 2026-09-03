"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, Goal, Priority, userId } from "../lib";

const options = { positions: ["产品经理","开发","算法","测试","数据分析","设计","运营","职能"], cities: ["北京","上海","深圳","杭州","成都","南京","武汉"], industries: ["互联网","AI","自动驾驶","游戏","金融","新能源"] };
const companies = ["腾讯","阿里巴巴","字节跳动","美团","京东","百度","华为","小米","网易","快手","拼多多","哔哩哔哩","滴滴","携程","蚂蚁集团","DeepSeek","MiniMax","月之暗面","智谱 AI","商汤科技","小米汽车","理想汽车","蔚来","小鹏汽车","比亚迪"];

export default function Onboarding() {
 const router = useRouter(); const [step,setStep]=useState(1); const [saving,setSaving]=useState(false);
 const [goal,setGoal]=useState<Goal>({graduation_year:"2027",target_positions:[],target_cities:[],target_industries:[],target_companies:[]});
 const toggle=(key:"target_positions"|"target_cities"|"target_industries", value:string)=>setGoal(g=>({...g,[key]:g[key].includes(value)?g[key].filter(x=>x!==value):[...g[key],value]}));
 const addCompany=(name:string)=>setGoal(g=>g.target_companies.some(c=>c.company_name===name)||g.target_companies.length>=10?g:{...g,target_companies:[...g.target_companies,{company_name:name,priority:"target"} ]});
 const setPriority=(name:string, priority:Priority)=>setGoal(g=>({...g,target_companies:g.target_companies.map(c=>c.company_name===name?{...c,priority}:c)}));
 async function save(){setSaving(true);try{await api(`/goals?user_id=${userId()}`,{method:"PATCH",body:JSON.stringify(goal)});router.push("/radar");}finally{setSaving(false)}}
 const canNext=step===1?goal.target_positions.length>0&&goal.target_cities.length>0&&goal.target_industries.length>0:goal.target_companies.length>0;
 return <div className="onboarding-page"><div className="onboarding-brand"><span className="brand-mark">CA</span> Campus Agent</div><div className="progress"><span style={{width:`${step*50}%`}}/></div><p className="step">第 {step} 步，共 2 步</p>
  {step===1?<section><p className="eyebrow">明确求职方向</p><h1>设置你的求职目标</h1><p className="lead">目标岗位、城市与行业将用于机会匹配和每日规划，之后可随时调整。</p>
   <Field title="你的求职届别"><div className="chips">{["2027","2028","社招"].map(x=><button className={goal.graduation_year===x?"selected":""} onClick={()=>setGoal({...goal,graduation_year:x})} key={x}>{x}{x!=="社招"&&" 届"}</button>)}</div></Field>
   <Field title="目标岗位（多选）"><div className="chips">{options.positions.map(x=><button className={goal.target_positions.includes(x)?"selected":""} onClick={()=>toggle("target_positions",x)} key={x}>{x}</button>)}</div></Field>
   <div className="two-fields"><Field title="目标城市（多选）"><div className="chips">{options.cities.map(x=><button className={goal.target_cities.includes(x)?"selected":""} onClick={()=>toggle("target_cities",x)} key={x}>{x}</button>)}</div></Field><Field title="目标行业（多选）"><div className="chips">{options.industries.map(x=><button className={goal.target_industries.includes(x)?"selected":""} onClick={()=>toggle("target_industries",x)} key={x}>{x}</button>)}</div></Field></div>
  </section>:<section><p className="eyebrow">设置关注优先级</p><h1>选择目标公司</h1><p className="lead">最多添加 10 家公司，并设置不同的关注级别。</p><div className="company-picker">{companies.map(name=><button key={name} className={goal.target_companies.some(c=>c.company_name===name)?"selected":""} onClick={()=>addCompany(name)}>{name}<span>＋</span></button>)}</div><div className="selected-companies">{goal.target_companies.map(c=><div key={c.company_name}><strong>{c.company_name}</strong><select value={c.priority} onChange={e=>setPriority(c.company_name,e.target.value as Priority)}><option value="dream">Dream · 冲刺</option><option value="target">Target · 重点</option><option value="safe">Safe · 保底</option></select><button onClick={()=>setGoal({...goal,target_companies:goal.target_companies.filter(x=>x.company_name!==c.company_name)})}>移除</button></div>)}</div></section>}
  <footer>{step===2&&<button className="secondary" onClick={()=>setStep(1)}>上一步</button>}<button className="primary large" disabled={!canNext||saving} onClick={()=>step===1?setStep(2):void save()}>{step===1?"继续选择目标公司":"生成我的秋招雷达"}</button></footer>
 </div>
}
function Field({title,children}:{title:string;children:React.ReactNode}){return <div className="field"><h3>{title}</h3>{children}</div>}
