/** Original Buxi types. Reference: ts-tarot-cards' separation of card / suit / spread. */
export type FriendId='feiyue'|'xingche'|'zhiwei';
export type Card={id:string;name:string;kind:string;position:string;reversed:boolean;prompt:string;arcana?:'major'|'minor';suit?:'wands'|'cups'|'swords'|'pentacles'|null;rank?:number;meanings?:{upright:string;reversed:string};source?:{name:string;url:string;revision:string;id:number}};
export type Reading={id:string;system:'tarot'|'sticks';question:string;spread:string;cards:Card[];created_at:string;interpretation:string;interpretation_source:string;algorithm_version:string;saved:boolean};
export type Message={role:string;content:string;memory_sources?:string[]};
export type Memory={id:string;friend:FriendId;content:string;source:string;active:boolean};
