import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Button from '../../../components/ui/Button';
import Card from '../../../components/ui/Card';
import apiClient from '../../../services/api/client';
import { unwrapList } from '../../../services/api/unwrap';
import { useCustomers } from '../../customers/hooks/use-customers';
import { useAuthStore } from '../../../store/auth.store';

const input = 'w-full h-10 px-3 border border-gray-200 rounded-lg';
const services = ['HANDLING_IN', 'HANDLING_OUT', 'STORAGE', 'VALUE_ADDED_SERVICE', 'OTHER'];
const bases = ['PER_TRANSACTION', 'PER_BAG_PER_DAY', 'PER_MT_PER_DAY', 'PER_SQFT_PER_MONTH', 'FIXED'];
export default function CustomerPricingPage() {
  const companyId = useAuthStore(s => s.companyContext);
  const client = useQueryClient(); const [show, setShow] = useState(false);
  const [form, setForm] = useState({ customer_id:'', code:'', name:'', valid_from:new Date().toISOString().slice(0,10), valid_to:'', service_type:'HANDLING_IN', calculation_basis:'PER_TRANSACTION', unit_rate:'', min_charge:'0' });
  const { data: customersData } = useCustomers({ page_size: 200, status:'ACTIVE' });
  const { data, isLoading } = useQuery({ queryKey:['customer-pricing'], queryFn: async()=>unwrapList(await apiClient.get('/rate-cards',{params:{page_size:200}})) });
  const create = useMutation({ mutationFn: d=>apiClient.post('/rate-cards',d), onSuccess:()=>{client.invalidateQueries({queryKey:['customer-pricing']});setShow(false);} });
  const save=async(e)=>{e.preventDefault();try{await create.mutateAsync({company_id:companyId,customer_id:form.customer_id,vendor_id:null,code:form.code,name:form.name,valid_from:`${form.valid_from}T00:00:00Z`,valid_to:form.valid_to?`${form.valid_to}T23:59:59Z`:null,currency:'INR',items:[{service_type:form.service_type,calculation_basis:form.calculation_basis,unit_rate:Number(form.unit_rate),min_charge:Number(form.min_charge),currency:'INR'}]});}catch(err){window.alert(err.response?.data?.message||err.message)}};
  const cards=(data?.items||[]).filter(x=>x.customer_id);
  return <div className="space-y-6"><PageHeader title="Customer Pricing Master" description="Effective-dated customer warehouse service rates." breadcrumbs={[{label:'Dashboard',to:'/dashboard'},{label:'Finance'},{label:'Customer Pricing'}]} actions={<Button onClick={()=>setShow(!show)}>New Pricing</Button>}/>
  {show&&<Card><Card.Body><form onSubmit={save} className="grid grid-cols-1 md:grid-cols-3 gap-4"><select required className={input} value={form.customer_id} onChange={e=>setForm({...form,customer_id:e.target.value})}><option value="">Select customer</option>{(customersData?.items||[]).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select><input required className={input} placeholder="Pricing code" value={form.code} onChange={e=>setForm({...form,code:e.target.value})}/><input required className={input} placeholder="Pricing name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><select className={input} value={form.service_type} onChange={e=>setForm({...form,service_type:e.target.value})}>{services.map(x=><option key={x}>{x}</option>)}</select><select className={input} value={form.calculation_basis} onChange={e=>setForm({...form,calculation_basis:e.target.value})}>{bases.map(x=><option key={x}>{x}</option>)}</select><input required type="number" min="0" step="0.0001" className={input} placeholder="Unit rate" value={form.unit_rate} onChange={e=>setForm({...form,unit_rate:e.target.value})}/><label>Effective From<input type="date" className={input} value={form.valid_from} onChange={e=>setForm({...form,valid_from:e.target.value})}/></label><label>Effective To<input type="date" className={input} value={form.valid_to} onChange={e=>setForm({...form,valid_to:e.target.value})}/></label><div className="flex items-end"><Button type="submit" isLoading={create.isPending}>Save Pricing</Button></div></form></Card.Body></Card>}
  <Card><div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="bg-gray-50">{['Customer','Code','Name','Effective From','Effective To','Services','Status'].map(h=><th key={h} className="p-3 text-left">{h}</th>)}</tr></thead><tbody>{isLoading?<tr><td colSpan="7" className="p-8 text-center">Loading…</td></tr>:cards.map(c=><tr key={c.id} className="border-t"><td className="p-3">{c.customer_name}</td><td className="p-3">{c.code}</td><td className="p-3">{c.name}</td><td className="p-3">{String(c.valid_from).slice(0,10)}</td><td className="p-3">{c.valid_to?String(c.valid_to).slice(0,10):'Open'}</td><td className="p-3">{c.items?.map(i=>`${i.service_type}: ₹${i.unit_rate}`).join(', ')}</td><td className="p-3">{c.status}</td></tr>)}</tbody></table></div></Card></div>;
}
